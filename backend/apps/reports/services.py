"""
Report generation services: Excel, PDF, CSV
"""
import csv
import io
import logging
from datetime import date
from decimal import Decimal

logger = logging.getLogger(__name__)


class ExcelReportService:
    """
    Generates .xlsx reports using openpyxl.
    Supports multiple sheets for different report types.
    """

    @staticmethod
    def generate_annual_report(year: int) -> bytes:
        """
        Generate a comprehensive annual report in Excel format.

        Sheets:
        - Summary
        - Revenue by Property
        - Expenses by Category
        - Payroll Summary
        - Reconciliation Status

        Returns:
            bytes of the .xlsx file
        """
        from openpyxl import Workbook
        from openpyxl.styles import (
            Font, PatternFill, Alignment, Border, Side, numbers
        )
        from openpyxl.utils import get_column_letter

        from apps.properties.services import calculate_all_revenue, get_property_revenue_breakdown
        from apps.properties.models import Property
        from apps.expenses.models import Expense, ExpenseAllocation
        from apps.payroll.models import PayrollPeriod
        from apps.banking.models import BankTransaction
        from django.db.models import Sum, Count

        wb = Workbook()

        # --- Styles ---
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
        subheader_fill = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
        alt_row_fill = PatternFill(start_color='EBF3FF', end_color='EBF3FF', fill_type='solid')
        total_font = Font(bold=True)
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin'),
        )
        currency_format = '#,##0.00 "CHF"'
        pct_format = '0.00%'

        def style_header_row(ws, row_num, col_count):
            for col in range(1, col_count + 1):
                cell = ws.cell(row=row_num, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.border = thin_border

        def auto_width(ws):
            for col in ws.columns:
                max_length = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_length + 4, 40)

        # ===== SHEET 1: Summary =====
        ws_summary = wb.active
        ws_summary.title = f'Summary {year}'
        ws_summary.freeze_panes = 'A2'

        revenue_data = calculate_all_revenue(year)
        expenses_total = Expense.objects.filter(
            expense_date__year=year, status__in=['APPROVED', 'PAID']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        payroll_total = PayrollPeriod.objects.filter(
            year=year, status__in=['FINAL', 'PAID']
        ).aggregate(total=Sum('total_employer_cost'))['total'] or Decimal('0')

        ws_summary.append([f'Annual Report {year}', '', '', ''])
        ws_summary['A1'].font = Font(bold=True, size=14)
        ws_summary.merge_cells('A1:D1')
        ws_summary.append(['Generated:', str(date.today()), '', ''])
        ws_summary.append([])

        headers = ['Category', 'Manager A', 'Manager B', 'Total']
        ws_summary.append(headers)
        style_header_row(ws_summary, ws_summary.max_row, 4)

        managers = sorted(revenue_data['managers'].values(), key=lambda x: x['manager_id'])
        rev_a = managers[0]['revenue'] if len(managers) > 0 else Decimal('0')
        rev_b = managers[1]['revenue'] if len(managers) > 1 else Decimal('0')

        ws_summary.append([
            'Revenue', float(rev_a), float(rev_b), float(revenue_data['total_revenue'])
        ])
        ws_summary.append([
            'Expenses (approved/paid)', '', '', float(expenses_total)
        ])
        ws_summary.append([
            'Payroll (employer cost)', '', '', float(payroll_total)
        ])
        net = revenue_data['total_revenue'] - Decimal(str(expenses_total)) - Decimal(str(payroll_total))
        net_row = ws_summary.max_row + 1
        ws_summary.append(['Net Result', '', '', float(net)])
        ws_summary.cell(row=net_row, column=1).font = total_font
        ws_summary.cell(row=net_row, column=4).font = total_font

        for row in ws_summary.iter_rows(min_row=5, max_row=ws_summary.max_row):
            for cell in row[1:]:
                if isinstance(cell.value, (int, float)):
                    cell.number_format = currency_format

        auto_width(ws_summary)

        # ===== SHEET 2: Revenue by Property =====
        ws_rev = wb.create_sheet(f'Revenue {year}')
        ws_rev.append([
            'Property ID', 'Property Name', 'Manager',
            'Annual Fee (CHF)', f'Revenue {year} (CHF)', 'Start Date', 'End Date',
        ])
        style_header_row(ws_rev, 1, 7)
        ws_rev.freeze_panes = 'A2'

        properties = Property.objects.select_related('assigned_manager').filter(is_active=True)
        from apps.properties.services import calculate_prorated_revenue

        for i, prop in enumerate(properties, 1):
            revenue = calculate_prorated_revenue(
                prop.annual_management_fee, prop.management_start_date,
                year, prop.management_end_date
            )
            row_data = [
                prop.unique_id, prop.name, prop.assigned_manager.full_name,
                float(prop.annual_management_fee), float(revenue),
                str(prop.management_start_date),
                str(prop.management_end_date) if prop.management_end_date else 'Active',
            ]
            ws_rev.append(row_data)
            if i % 2 == 0:
                for cell in ws_rev[ws_rev.max_row]:
                    cell.fill = alt_row_fill

        auto_width(ws_rev)

        # ===== SHEET 3: Expenses =====
        ws_exp = wb.create_sheet(f'Expenses {year}')
        ws_exp.append([
            'Expense ID', 'Title', 'Vendor', 'Category', 'Amount (CHF)',
            'Date', 'Status', 'Allocation Method',
        ])
        style_header_row(ws_exp, 1, 8)
        ws_exp.freeze_panes = 'A2'

        expenses = Expense.objects.filter(
            expense_date__year=year
        ).order_by('expense_date')

        for i, exp in enumerate(expenses, 1):
            ws_exp.append([
                exp.unique_id, exp.title, exp.vendor_name,
                exp.get_category_display(), float(exp.amount),
                str(exp.expense_date), exp.get_status_display(),
                exp.get_allocation_method_display(),
            ])
            if i % 2 == 0:
                for cell in ws_exp[ws_exp.max_row]:
                    cell.fill = alt_row_fill

        auto_width(ws_exp)

        # ===== SHEET 4: Payroll =====
        ws_pay = wb.create_sheet(f'Payroll {year}')
        ws_pay.append([
            'Employee', 'Year', 'Month', 'Gross (CHF)',
            'AHV Employee', 'ALV Employee', 'BVG Employee',
            'Total Deductions', 'Net (CHF)', 'Employer Cost (CHF)', 'Status',
        ])
        style_header_row(ws_pay, 1, 11)
        ws_pay.freeze_panes = 'A2'

        periods = PayrollPeriod.objects.filter(
            year=year
        ).select_related('employee').order_by('employee__last_name', 'month')

        for i, period in enumerate(periods, 1):
            ws_pay.append([
                period.employee.full_name, period.year, period.month,
                float(period.gross_salary),
                float(period.ahv_employee), float(period.alv_employee), float(period.bvg_employee),
                float(period.total_deductions_employee), float(period.net_salary),
                float(period.total_employer_cost), period.get_status_display(),
            ])
            if i % 2 == 0:
                for cell in ws_pay[ws_pay.max_row]:
                    cell.fill = alt_row_fill

        auto_width(ws_pay)

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def generate_expense_report(year: int, manager_id: int = None) -> bytes:
        """Generate expense allocation report, optionally filtered by manager."""
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from apps.expenses.models import ExpenseAllocation
        from django.db.models import Sum

        wb = Workbook()
        ws = wb.active
        ws.title = 'Expense Allocations'

        headers = [
            'Expense ID', 'Title', 'Amount Total', 'Date',
            'Category', 'Allocation Method', 'Manager', 'Allocated Amount', 'Percentage',
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')

        qs = ExpenseAllocation.objects.filter(
            expense__expense_date__year=year,
            expense__status__in=['APPROVED', 'PAID'],
        ).select_related('expense', 'manager').order_by('expense__expense_date')

        if manager_id:
            qs = qs.filter(manager_id=manager_id)

        for alloc in qs:
            ws.append([
                alloc.expense.unique_id,
                alloc.expense.title,
                float(alloc.expense.amount),
                str(alloc.expense.expense_date),
                alloc.expense.get_category_display(),
                alloc.expense.get_allocation_method_display(),
                alloc.manager.full_name,
                float(alloc.amount),
                float(alloc.percentage / 100),
            ])

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()


class PDFReportService:
    """
    Generates audit-ready PDF reports using ReportLab.
    """

    @staticmethod
    def generate_annual_summary_pdf(year: int) -> bytes:
        """Generate an audit-ready annual summary PDF."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak,
        )
        from apps.properties.services import calculate_all_revenue
        from apps.expenses.models import Expense
        from apps.payroll.models import PayrollPeriod
        from django.db.models import Sum

        output = io.BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=18,
            spaceAfter=12,
            textColor=colors.HexColor('#1F4E79'),
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=8,
            textColor=colors.HexColor('#2E75B6'),
        )
        normal_style = styles['Normal']
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
        )

        table_header_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EBF3FF')]),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]

        story = []

        # Title
        story.append(Paragraph(
            f'Swiss Property Management – Annual Report {year}',
            title_style
        ))
        story.append(Paragraph(
            f'Reporting period: 1 January {year} – 31 December {year}',
            normal_style
        ))
        story.append(Paragraph(
            f'Generated: {date.today().strftime("%d.%m.%Y")}',
            footer_style
        ))
        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#2E75B6')))
        story.append(Spacer(1, 0.5 * cm))

        # Revenue section
        story.append(Paragraph('1. Revenue Overview', heading_style))
        revenue_data = calculate_all_revenue(year)
        rev_table_data = [['Manager', 'Properties', 'Revenue (CHF)', 'Share (%)']]
        for mid, mdata in revenue_data['managers'].items():
            pct = revenue_data['percentages'].get(mid, Decimal('0'))
            rev_table_data.append([
                mdata['manager_name'],
                str(mdata['property_count']),
                f"{float(mdata['revenue']):,.2f}",
                f"{float(pct):.2f}%",
            ])
        rev_table_data.append([
            'TOTAL', '', f"{float(revenue_data['total_revenue']):,.2f}", '100.00%'
        ])

        rev_table = Table(rev_table_data, colWidths=[8 * cm, 3 * cm, 5 * cm, 3 * cm])
        rev_table.setStyle(TableStyle(table_header_style + [
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1F4E79')),
        ]))
        story.append(rev_table)
        story.append(Spacer(1, 0.5 * cm))

        # Expenses section
        story.append(Paragraph('2. Expense Summary', heading_style))
        expense_agg = Expense.objects.filter(
            expense_date__year=year
        ).values('status').annotate(
            count=Sum('amount') * 0 + models_count_int(),
            total=Sum('amount'),
        ).order_by('status')

        exp_table_data = [['Status', 'Count', 'Total (CHF)']]
        grand_total = Decimal('0')
        for row in expense_agg:
            exp_table_data.append([
                row['status'],
                str(row['count']),
                f"{float(row['total'] or 0):,.2f}",
            ])
            grand_total += Decimal(str(row['total'] or 0))
        exp_table_data.append(['TOTAL', '', f"{float(grand_total):,.2f}"])

        exp_table = Table(exp_table_data, colWidths=[8 * cm, 4 * cm, 7 * cm])
        exp_table.setStyle(TableStyle(table_header_style + [
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(exp_table)
        story.append(Spacer(1, 0.5 * cm))

        # Payroll section
        story.append(Paragraph('3. Payroll Summary', heading_style))
        payroll_agg = PayrollPeriod.objects.filter(year=year).aggregate(
            total_gross=Sum('gross_salary'),
            total_net=Sum('net_salary'),
            total_employer=Sum('total_employer_cost'),
        )
        pay_table_data = [
            ['Description', 'Amount (CHF)'],
            ['Total Gross Salary', f"{float(payroll_agg['total_gross'] or 0):,.2f}"],
            ['Total Net Salary', f"{float(payroll_agg['total_net'] or 0):,.2f}"],
            ['Total Employer Cost', f"{float(payroll_agg['total_employer'] or 0):,.2f}"],
        ]
        pay_table = Table(pay_table_data, colWidths=[11 * cm, 8 * cm])
        pay_table.setStyle(TableStyle(table_header_style))
        story.append(pay_table)
        story.append(Spacer(1, 0.5 * cm))

        # Net result
        story.append(Paragraph('4. Net Result', heading_style))
        total_rev = revenue_data['total_revenue']
        total_exp = grand_total
        total_pay = Decimal(str(payroll_agg['total_employer'] or 0))
        net = total_rev - total_exp - total_pay

        net_table_data = [
            ['Item', 'Amount (CHF)'],
            ['Total Revenue', f"{float(total_rev):,.2f}"],
            ['Total Expenses', f"-{float(total_exp):,.2f}"],
            ['Total Payroll (employer cost)', f"-{float(total_pay):,.2f}"],
            ['NET RESULT', f"{float(net):,.2f}"],
        ]
        net_table = Table(net_table_data, colWidths=[11 * cm, 8 * cm])
        net_table.setStyle(TableStyle(table_header_style + [
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (1, -1), (1, -1),
             colors.HexColor('#006400') if net >= 0 else colors.red),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1F4E79')),
        ]))
        story.append(net_table)
        story.append(Spacer(1, cm))

        # Footer
        story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
        story.append(Paragraph(
            f'This report was automatically generated by the Swiss Property Management '
            f'Accounting Platform on {date.today().strftime("%d.%m.%Y")}. '
            f'All figures in CHF. This document is for internal use only.',
            footer_style
        ))

        doc.build(story)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def generate_payslip_pdf(payroll_period) -> bytes:
        """Generate a payslip (Lohnabrechnung) PDF for a payroll period."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        import calendar

        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4,
                                rightMargin=2.5*cm, leftMargin=2.5*cm,
                                topMargin=2.5*cm, bottomMargin=2.5*cm)

        styles = getSampleStyleSheet()
        story = []

        month_name = calendar.month_name[payroll_period.month]
        story.append(Paragraph(
            f'Lohnabrechnung {month_name} {payroll_period.year}',
            styles['Title']
        ))
        story.append(Paragraph(
            f'Mitarbeitende: {payroll_period.employee.full_name}',
            styles['Normal']
        ))
        story.append(Spacer(1, 0.5*cm))

        deduction_data = [
            ['Beschreibung', 'Betrag (CHF)'],
            ['Bruttolohn', f"{float(payroll_period.gross_salary):,.2f}"],
            ['', ''],
            ['Abzüge Arbeitnehmer:', ''],
            ['AHV-Beiträge (AN)', f"-{float(payroll_period.ahv_employee):,.2f}"],
            ['IV-Beiträge (AN)', f"-{float(payroll_period.iv_employee):,.2f}"],
            ['EO-Beiträge (AN)', f"-{float(payroll_period.eo_employee):,.2f}"],
            ['ALV-Beiträge (AN)', f"-{float(payroll_period.alv_employee):,.2f}"],
            ['NBU-Prämie (AN)', f"-{float(payroll_period.nbu_employee):,.2f}"],
            ['BVG-Beiträge (AN)', f"-{float(payroll_period.bvg_employee):,.2f}"],
            ['KTG (AN)', f"-{float(payroll_period.ktg_employee):,.2f}"],
            ['Total Abzüge', f"-{float(payroll_period.total_deductions_employee):,.2f}"],
            ['', ''],
            ['NETTOLOHN', f"{float(payroll_period.net_salary):,.2f}"],
        ]

        table = Table(deduction_data, colWidths=[10*cm, 6*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        story.append(table)

        doc.build(story)
        output.seek(0)
        return output.getvalue()


def models_count_int():
    from django.db.models import Count
    return Count('id')


class CSVExportService:
    """Generates CSV export files."""

    @staticmethod
    def export_expenses(year: int, manager_id: int = None) -> str:
        """Export expenses to CSV string."""
        from apps.expenses.models import Expense

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Expense ID', 'Title', 'Vendor', 'Amount', 'Currency',
            'Date', 'Category', 'Status', 'Allocation Method',
            'VAT Amount', 'Net Amount', 'Is QR Bill',
        ])

        qs = Expense.objects.filter(expense_date__year=year).order_by('expense_date')
        if manager_id:
            qs = qs.filter(allocations__manager_id=manager_id).distinct()

        for exp in qs:
            writer.writerow([
                exp.unique_id, exp.title, exp.vendor_name,
                exp.amount, exp.currency, exp.expense_date,
                exp.category, exp.status, exp.allocation_method,
                exp.vat_amount, exp.net_amount, exp.is_qr_bill,
            ])

        return output.getvalue()

    @staticmethod
    def export_payroll(year: int) -> str:
        """Export payroll periods to CSV string."""
        from apps.payroll.models import PayrollPeriod

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Employee', 'Year', 'Month', 'Gross Salary',
            'AHV Employee', 'IV Employee', 'EO Employee',
            'ALV Employee', 'NBU Employee', 'BVG Employee', 'KTG Employee',
            'Total Deductions', 'Net Salary',
            'AHV Employer', 'ALV Employer', 'BVG Employer',
            'Total Employer Cost', 'Status',
        ])

        periods = PayrollPeriod.objects.filter(year=year).select_related('employee')
        for period in periods:
            writer.writerow([
                period.employee.full_name,
                period.year, period.month,
                period.gross_salary,
                period.ahv_employee, period.iv_employee, period.eo_employee,
                period.alv_employee, period.nbu_employee, period.bvg_employee, period.ktg_employee,
                period.total_deductions_employee, period.net_salary,
                period.ahv_employer, period.alv_employer, period.bvg_employer,
                period.total_employer_cost, period.status,
            ])

        return output.getvalue()

    @staticmethod
    def export_transactions(year: int) -> str:
        """Export bank transactions to CSV string."""
        from apps.banking.models import BankTransaction

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Transaction ID', 'Account', 'Date', 'Value Date',
            'Amount', 'Currency', 'Type', 'Description',
            'Counterparty', 'Counterparty IBAN',
            'Reconciled', 'Status', 'Reference',
        ])

        txs = BankTransaction.objects.filter(
            transaction_date__year=year
        ).select_related('bank_account')

        for tx in txs:
            writer.writerow([
                tx.unique_id, tx.bank_account.name,
                tx.transaction_date, tx.value_date,
                tx.amount, tx.currency, tx.transaction_type,
                tx.description, tx.counterparty_name, tx.counterparty_iban,
                tx.is_reconciled, tx.status, tx.reference,
            ])

        return output.getvalue()

    @staticmethod
    def export_revenue(year: int) -> str:
        """Export revenue by property to CSV string."""
        from apps.properties.models import Property
        from apps.properties.services import calculate_prorated_revenue

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Property ID', 'Name', 'Address', 'Manager',
            'Annual Fee', 'Start Date', 'End Date', f'Revenue {year}',
        ])

        properties = Property.objects.select_related('assigned_manager').order_by('name')
        for prop in properties:
            revenue = calculate_prorated_revenue(
                prop.annual_management_fee,
                prop.management_start_date,
                year,
                prop.management_end_date,
            )
            writer.writerow([
                prop.unique_id, prop.name, prop.address,
                prop.assigned_manager.full_name,
                prop.annual_management_fee,
                prop.management_start_date,
                prop.management_end_date or '',
                revenue,
            ])

        return output.getvalue()
