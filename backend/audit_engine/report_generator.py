"""
Report Generation System - Step 6
Comprehensive report generation for audit results in multiple formats.
"""

import os
import json
import csv
import html
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import asdict
import logging

from .models_audit import (
    AuditRun, PolicyAuditResult, AuditSummary, ReportFormat, 
    ComplianceResult, AuditSeverity, ReportTemplate
)

# =================================================================
# REPORT GENERATION ENGINE
# =================================================================

class ReportGenerator:
    """
    Comprehensive report generator for audit results.
    Supports HTML, PDF, CSV, JSON, and Excel formats.
    """
    
    def __init__(self, reports_dir: str = "reports"):
        """Initialize report generator with output directory"""
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger("ReportGenerator")
        
        # Load report templates
        self.templates = self._load_report_templates()
    
    def _load_report_templates(self) -> Dict[str, ReportTemplate]:
        """Load report templates from configuration"""
        templates = {}
        
        # Default templates
        templates["standard"] = ReportTemplate(
            name="Standard CIS Audit Report",
            description="Comprehensive audit report with all sections",
            include_executive_summary=True,
            include_detailed_results=True,
            include_remediation_guide=True,
            include_trend_analysis=False,
            include_system_info=True,
            show_passed_policies=False,
            show_failed_policies=True,
            show_errors=True
        )
        
        templates["executive"] = ReportTemplate(
            name="Executive Summary Report",
            description="High-level summary for executives",
            include_executive_summary=True,
            include_detailed_results=False,
            include_remediation_guide=False,
            include_trend_analysis=True,
            include_system_info=False,
            show_passed_policies=False,
            show_failed_policies=True,
            show_errors=False,
            minimum_severity=AuditSeverity.HIGH
        )
        
        templates["technical"] = ReportTemplate(
            name="Technical Implementation Report",
            description="Detailed technical report for IT teams",
            include_executive_summary=False,
            include_detailed_results=True,
            include_remediation_guide=True,
            include_trend_analysis=False,
            include_system_info=True,
            show_passed_policies=True,
            show_failed_policies=True,
            show_errors=True
        )
        
        return templates
    
    def generate_report(self, audit_run: AuditRun, format: ReportFormat, 
                       template_name: str = "standard") -> str:
        """Generate audit report in specified format"""
        try:
            template = self.templates.get(template_name, self.templates["standard"])
            
            if format == ReportFormat.HTML:
                return self._generate_html_report(audit_run, template)
            elif format == ReportFormat.PDF:
                return self._generate_pdf_report(audit_run, template)
            elif format == ReportFormat.CSV:
                return self._generate_csv_report(audit_run, template)
            elif format == ReportFormat.JSON:
                return self._generate_json_report(audit_run, template)
            elif format == ReportFormat.EXCEL:
                return self._generate_excel_report(audit_run, template)
            else:
                raise ValueError(f"Unsupported report format: {format}")
                
        except Exception as e:
            self.logger.error(f"Failed to generate {format.value} report: {e}")
            raise
    
    def _generate_html_report(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Generate comprehensive HTML report"""
        try:
            report_filename = f"audit_report_{audit_run.audit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            # Filter results based on template settings
            filtered_results = self._filter_results(audit_run.policy_results, template)
            
            html_content = self._build_html_report(audit_run, filtered_results, template)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Generated HTML report: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate HTML report: {e}")
            raise
    
    def _build_html_report(self, audit_run: AuditRun, results: List[PolicyAuditResult], 
                          template: ReportTemplate) -> str:
        """Build complete HTML report content"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template.report_title}</title>
    <style>
        {self._get_default_css()}
        {template.custom_css or ''}
    </style>
</head>
<body>
    <div class="report-container">
        {self._build_report_header(audit_run, template)}
        
        {self._build_executive_summary(audit_run, template) if template.include_executive_summary else ''}
        
        {self._build_system_info_section(audit_run, template) if template.include_system_info else ''}
        
        {self._build_summary_section(audit_run.summary, template)}
        
        {self._build_detailed_results_section(results, template) if template.include_detailed_results else ''}
        
        {self._build_remediation_guide_section(results, template) if template.include_remediation_guide else ''}
        
        {self._build_report_footer(audit_run, template)}
    </div>
    
    <script>
        {self._get_report_javascript()}
    </script>
</body>
</html>"""
        
        return html
    
    def _get_default_css(self) -> str:
        """Get default CSS styles for HTML reports"""
        return """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        
        .report-header {
            text-align: center;
            border-bottom: 3px solid #0066cc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .report-title {
            font-size: 28px;
            color: #0066cc;
            margin-bottom: 10px;
        }
        
        .report-subtitle {
            font-size: 16px;
            color: #666;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section-title {
            font-size: 22px;
            color: #0066cc;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 5px;
            margin-bottom: 20px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .summary-card {
            background: #f8f9fa;
            padding: 20px;
            border-left: 5px solid #0066cc;
            border-radius: 5px;
        }
        
        .summary-card.critical {
            border-left-color: #dc3545;
        }
        
        .summary-card.high {
            border-left-color: #fd7e14;
        }
        
        .summary-card.medium {
            border-left-color: #ffc107;
        }
        
        .summary-card.low {
            border-left-color: #28a745;
        }
        
        .summary-value {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .summary-label {
            font-size: 14px;
            color: #666;
        }
        
        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .results-table th,
        .results-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .results-table th {
            background-color: #0066cc;
            color: white;
            font-weight: 600;
        }
        
        .results-table tr:hover {
            background-color: #f5f5f5;
        }
        
        .result-pass {
            color: #28a745;
            font-weight: bold;
        }
        
        .result-fail {
            color: #dc3545;
            font-weight: bold;
        }
        
        .result-error {
            color: #fd7e14;
            font-weight: bold;
        }
        
        .result-na {
            color: #6c757d;
            font-weight: bold;
        }
        
        .severity-critical {
            background-color: #dc3545;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .severity-high {
            background-color: #fd7e14;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .severity-medium {
            background-color: #ffc107;
            color: black;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .severity-low {
            background-color: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        
        .collapsible {
            cursor: pointer;
            user-select: none;
        }
        
        .collapsible:hover {
            background-color: #f0f0f0;
        }
        
        .collapsible-content {
            display: none;
            padding: 10px;
            background-color: #f8f9fa;
            border-left: 3px solid #0066cc;
            margin-top: 10px;
        }
        
        .collapsible-content.show {
            display: block;
        }
        
        .remediation-box {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-left: 5px solid #ffc107;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        
        .system-info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .system-info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        
        .system-info-label {
            font-weight: 600;
            color: #666;
        }
        
        .chart-container {
            width: 100%;
            height: 300px;
            margin: 20px 0;
        }
        
        .progress-bar {
            width: 100%;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 30px;
            background-color: #28a745;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.3s ease;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 14px;
        }
        
        @media print {
            .report-container {
                box-shadow: none;
                max-width: none;
            }
            
            .collapsible-content {
                display: block !important;
            }
        }
        """
    
    def _build_report_header(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Build report header section"""
        return f"""
        <div class="report-header">
            <h1 class="report-title">{html.escape(template.report_title)}</h1>
            <div class="report-subtitle">
                <p><strong>{html.escape(template.company_name)}</strong></p>
                <p>Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                <p>Audit ID: {audit_run.audit_id}</p>
            </div>
        </div>
        """
    
    def _build_executive_summary(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Build executive summary section"""
        if not audit_run.summary:
            return ""
        
        summary = audit_run.summary
        compliance_level = "Excellent" if summary.compliance_percentage >= 90 else \
                          "Good" if summary.compliance_percentage >= 80 else \
                          "Fair" if summary.compliance_percentage >= 60 else \
                          "Poor"
        
        return f"""
        <div class="section">
            <h2 class="section-title">Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-value">{summary.compliance_percentage:.1f}%</div>
                    <div class="summary-label">Overall Compliance</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary.total_policies}</div>
                    <div class="summary-label">Total Policies Audited</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary.failed_policies}</div>
                    <div class="summary-label">Failed Policies</div>
                </div>
                <div class="summary-card critical">
                    <div class="summary-value">{summary.critical_issues}</div>
                    <div class="summary-label">Critical Issues</div>
                </div>
            </div>
            
            <div class="progress-bar">
                <div class="progress-fill" style="width: {summary.compliance_percentage}%">
                    {summary.compliance_percentage:.1f}% Compliant
                </div>
            </div>
            
            <p><strong>Compliance Level:</strong> {compliance_level}</p>
            <p><strong>System:</strong> {html.escape(audit_run.system_info.hostname)} 
               ({html.escape(audit_run.system_info.os_version)})</p>
            <p><strong>Audit Date:</strong> {audit_run.start_time.strftime('%B %d, %Y') if audit_run.start_time else 'Unknown'}</p>
            
            {self._build_key_findings(audit_run.policy_results)}
        </div>
        """
    
    def _build_key_findings(self, results: List[PolicyAuditResult]) -> str:
        """Build key findings section"""
        critical_failures = [r for r in results if r.result == ComplianceResult.FAIL and r.severity == AuditSeverity.CRITICAL]
        high_failures = [r for r in results if r.result == ComplianceResult.FAIL and r.severity == AuditSeverity.HIGH]
        
        if not critical_failures and not high_failures:
            return "<p><strong>Key Findings:</strong> No critical or high-severity issues identified.</p>"
        
        findings_html = "<h3>Key Findings:</h3><ul>"
        
        for failure in critical_failures[:3]:  # Show top 3 critical
            findings_html += f"<li><strong>Critical:</strong> {html.escape(failure.policy_name)} - {html.escape(failure.error_message or 'Failed compliance check')}</li>"
        
        for failure in high_failures[:3]:  # Show top 3 high
            findings_html += f"<li><strong>High:</strong> {html.escape(failure.policy_name)} - {html.escape(failure.error_message or 'Failed compliance check')}</li>"
        
        findings_html += "</ul>"
        
        if len(critical_failures) + len(high_failures) > 6:
            findings_html += f"<p><em>And {len(critical_failures) + len(high_failures) - 6} more high/critical issues...</em></p>"
        
        return findings_html
    
    def _build_system_info_section(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Build system information section"""
        system = audit_run.system_info
        
        return f"""
        <div class="section">
            <h2 class="section-title">System Information</h2>
            <div class="system-info-grid">
                <div>
                    <div class="system-info-item">
                        <span class="system-info-label">Hostname:</span>
                        <span>{html.escape(system.hostname)}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Operating System:</span>
                        <span>{html.escape(system.os_version)}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Build:</span>
                        <span>{html.escape(system.os_build)}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Architecture:</span>
                        <span>{html.escape(system.architecture)}</span>
                    </div>
                </div>
                <div>
                    <div class="system-info-item">
                        <span class="system-info-label">Domain/Workgroup:</span>
                        <span>{html.escape(system.domain or system.workgroup or 'Unknown')}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Scan Time:</span>
                        <span>{system.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Last Boot:</span>
                        <span>{system.last_boot.strftime('%Y-%m-%d %H:%M:%S') if system.last_boot else 'Unknown'}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Total Memory:</span>
                        <span>{self._format_bytes(system.total_memory) if system.total_memory else 'Unknown'}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_summary_section(self, summary: Optional[AuditSummary], template: ReportTemplate) -> str:
        """Build audit summary section"""
        if not summary:
            return ""
        
        return f"""
        <div class="section">
            <h2 class="section-title">Audit Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-value">{summary.passed_policies}</div>
                    <div class="summary-label">Passed Policies</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary.failed_policies}</div>
                    <div class="summary-label">Failed Policies</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary.error_policies}</div>
                    <div class="summary-label">Error Policies</div>
                </div>
                <div class="summary-card">
                    <div class="summary-value">{summary.not_applicable_policies}</div>
                    <div class="summary-label">Not Applicable</div>
                </div>
            </div>
            
            <h3>Issues by Severity</h3>
            <div class="summary-grid">
                <div class="summary-card critical">
                    <div class="summary-value">{summary.critical_issues}</div>
                    <div class="summary-label">Critical Issues</div>
                </div>
                <div class="summary-card high">
                    <div class="summary-value">{summary.high_issues}</div>
                    <div class="summary-label">High Priority Issues</div>
                </div>
                <div class="summary-card medium">
                    <div class="summary-value">{summary.medium_issues}</div>
                    <div class="summary-label">Medium Priority Issues</div>
                </div>
                <div class="summary-card low">
                    <div class="summary-value">{summary.low_issues}</div>
                    <div class="summary-label">Low Priority Issues</div>
                </div>
            </div>
            
            <h3>Performance Metrics</h3>
            <div class="system-info-grid">
                <div>
                    <div class="system-info-item">
                        <span class="system-info-label">Total Execution Time:</span>
                        <span>{self._format_duration(summary.total_execution_time_ms)}</span>
                    </div>
                    <div class="system-info-item">
                        <span class="system-info-label">Average Policy Time:</span>
                        <span>{summary.average_policy_time_ms:.1f} ms</span>
                    </div>
                </div>
                <div>
                    <div class="system-info-item">
                        <span class="system-info-label">Security Score:</span>
                        <span>{summary.security_score:.1f}/100</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _build_detailed_results_section(self, results: List[PolicyAuditResult], template: ReportTemplate) -> str:
        """Build detailed results section"""
        if not results:
            return ""
        
        table_rows = ""
        for result in results:
            result_class = self._get_result_class(result.result)
            severity_class = f"severity-{result.severity.value}"
            
            table_rows += f"""
            <tr class="collapsible">
                <td>{html.escape(result.policy_name)}</td>
                <td>{html.escape(result.category)}</td>
                <td class="{result_class}">{result.result.value.upper()}</td>
                <td><span class="{severity_class}">{result.severity.value.upper()}</span></td>
                <td>{result.cis_level}</td>
                <td>{result.execution_time_ms} ms</td>
            </tr>
            <tr>
                <td colspan="6">
                    <div class="collapsible-content">
                        <p><strong>Description:</strong> {html.escape(result.description)}</p>
                        {f'<p><strong>Current Value:</strong> {html.escape(result.current_value)}</p>' if result.current_value else ''}
                        {f'<p><strong>Expected Value:</strong> {html.escape(result.expected_value)}</p>' if result.expected_value else ''}
                        {f'<p><strong>Registry Path:</strong> {html.escape(result.registry_path)}</p>' if result.registry_path else ''}
                        {f'<p><strong>Error:</strong> {html.escape(result.error_message)}</p>' if result.error_message else ''}
                        {f'<div class="remediation-box"><strong>Remediation:</strong> {html.escape(result.remediation)}</div>' if result.remediation else ''}
                    </div>
                </td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">Detailed Results</h2>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Policy Name</th>
                        <th>Category</th>
                        <th>Result</th>
                        <th>Severity</th>
                        <th>CIS Level</th>
                        <th>Execution Time</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        """
    
    def _build_remediation_guide_section(self, results: List[PolicyAuditResult], template: ReportTemplate) -> str:
        """Build remediation guide section"""
        failed_results = [r for r in results if r.result == ComplianceResult.FAIL and r.remediation]
        
        if not failed_results:
            return ""
        
        remediation_items = ""
        for result in failed_results[:20]:  # Limit to top 20 for readability
            severity_class = f"severity-{result.severity.value}"
            remediation_items += f"""
            <div class="remediation-box">
                <h4>{html.escape(result.policy_name)} <span class="{severity_class}">{result.severity.value.upper()}</span></h4>
                <p><strong>Issue:</strong> {html.escape(result.error_message or 'Policy compliance check failed')}</p>
                <p><strong>Current Value:</strong> {html.escape(result.current_value or 'Not detected')}</p>
                <p><strong>Expected Value:</strong> {html.escape(result.expected_value or 'See CIS documentation')}</p>
                <p><strong>Remediation:</strong> {html.escape(result.remediation)}</p>
                {f'<p><strong>Registry Path:</strong> {html.escape(result.registry_path)}</p>' if result.registry_path else ''}
            </div>
            """
        
        return f"""
        <div class="section">
            <h2 class="section-title">Remediation Guide</h2>
            <p>The following section provides specific remediation steps for failed policy checks.</p>
            {remediation_items}
            {f'<p><em>Note: {len(failed_results) - 20} additional remediation items not shown for brevity.</em></p>' if len(failed_results) > 20 else ''}
        </div>
        """
    
    def _build_report_footer(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Build report footer"""
        return f"""
        <div class="footer">
            <p>This report was generated by the CIS GPO Compliance Tool on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p>Audit ID: {audit_run.audit_id} | Report Version: 1.0</p>
            <p>&copy; {datetime.now().year} {html.escape(template.company_name)}. All rights reserved.</p>
        </div>
        """
    
    def _get_report_javascript(self) -> str:
        """Get JavaScript for interactive report features"""
        return """
        document.addEventListener('DOMContentLoaded', function() {
            // Make table rows collapsible
            const collapsibles = document.querySelectorAll('.collapsible');
            collapsibles.forEach(function(collapsible) {
                collapsible.addEventListener('click', function() {
                    const nextRow = this.nextElementSibling;
                    const content = nextRow.querySelector('.collapsible-content');
                    if (content) {
                        content.classList.toggle('show');
                    }
                });
            });
            
            // Add print functionality
            if (window.print) {
                const printBtn = document.createElement('button');
                printBtn.innerHTML = 'Print Report';
                printBtn.style.position = 'fixed';
                printBtn.style.top = '10px';
                printBtn.style.right = '10px';
                printBtn.style.padding = '10px 20px';
                printBtn.style.backgroundColor = '#0066cc';
                printBtn.style.color = 'white';
                printBtn.style.border = 'none';
                printBtn.style.borderRadius = '5px';
                printBtn.style.cursor = 'pointer';
                printBtn.style.zIndex = '1000';
                printBtn.onclick = function() { window.print(); };
                document.body.appendChild(printBtn);
            }
        });
        """
    
    def _generate_csv_report(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Generate CSV report"""
        try:
            report_filename = f"audit_report_{audit_run.audit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            # Filter results based on template settings
            filtered_results = self._filter_results(audit_run.policy_results, template)
            
            with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Policy ID', 'Policy Name', 'Category', 'CIS Level', 'Result', 
                    'Severity', 'Current Value', 'Expected Value', 'Registry Path', 
                    'Registry Key', 'Error Message', 'Remediation', 'Execution Time (ms)'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in filtered_results:
                    writer.writerow({
                        'Policy ID': result.policy_id,
                        'Policy Name': result.policy_name,
                        'Category': result.category,
                        'CIS Level': result.cis_level,
                        'Result': result.result.value,
                        'Severity': result.severity.value,
                        'Current Value': result.current_value or '',
                        'Expected Value': result.expected_value or '',
                        'Registry Path': result.registry_path or '',
                        'Registry Key': result.registry_key or '',
                        'Error Message': result.error_message or '',
                        'Remediation': result.remediation or '',
                        'Execution Time (ms)': result.execution_time_ms
                    })
            
            self.logger.info(f"Generated CSV report: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate CSV report: {e}")
            raise
    
    def _generate_json_report(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Generate JSON report"""
        try:
            report_filename = f"audit_report_{audit_run.audit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            # Filter results based on template settings
            filtered_results = self._filter_results(audit_run.policy_results, template)
            
            report_data = {
                "report_info": {
                    "audit_id": audit_run.audit_id,
                    "generated_at": datetime.now().isoformat(),
                    "template_name": template.name,
                    "report_version": "1.0"
                },
                "system_info": asdict(audit_run.system_info) if template.include_system_info else None,
                "audit_configuration": asdict(audit_run.configuration),
                "summary": asdict(audit_run.summary) if audit_run.summary else None,
                "results": [asdict(result) for result in filtered_results]
            }
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(f"Generated JSON report: {report_path}")
            return report_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate JSON report: {e}")
            raise
    
    def _generate_pdf_report(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Generate PDF report (placeholder - requires additional library)"""
        try:
            # For now, generate HTML and suggest PDF conversion
            html_path = self._generate_html_report(audit_run, template)
            
            # PDF generation would require libraries like weasyprint or reportlab
            # For now, return the HTML path with a note
            self.logger.info(f"PDF generation not implemented. Generated HTML report: {html_path}")
            return html_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate PDF report: {e}")
            raise
    
    def _generate_excel_report(self, audit_run: AuditRun, template: ReportTemplate) -> str:
        """Generate Excel report (placeholder - requires additional library)"""
        try:
            # For now, generate CSV and suggest Excel conversion
            csv_path = self._generate_csv_report(audit_run, template)
            
            # Excel generation would require libraries like openpyxl or xlsxwriter
            # For now, return the CSV path with a note
            self.logger.info(f"Excel generation not implemented. Generated CSV report: {csv_path}")
            return csv_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate Excel report: {e}")
            raise
    
    def _filter_results(self, results: List[PolicyAuditResult], template: ReportTemplate) -> List[PolicyAuditResult]:
        """Filter results based on template settings"""
        filtered = []
        
        for result in results:
            # Filter by result type
            if result.result == ComplianceResult.PASS and not template.show_passed_policies:
                continue
            if result.result == ComplianceResult.FAIL and not template.show_failed_policies:
                continue
            if result.result == ComplianceResult.ERROR and not template.show_errors:
                continue
            
            # Filter by severity
            severity_order = {
                AuditSeverity.INFORMATIONAL: 0,
                AuditSeverity.LOW: 1,
                AuditSeverity.MEDIUM: 2,
                AuditSeverity.HIGH: 3,
                AuditSeverity.CRITICAL: 4
            }
            
            if severity_order.get(result.severity, 0) < severity_order.get(template.minimum_severity, 0):
                continue
            
            filtered.append(result)
        
        return filtered
    
    def _get_result_class(self, result: ComplianceResult) -> str:
        """Get CSS class for result type"""
        return {
            ComplianceResult.PASS: "result-pass",
            ComplianceResult.FAIL: "result-fail",
            ComplianceResult.ERROR: "result-error",
            ComplianceResult.NOT_APPLICABLE: "result-na",
            ComplianceResult.MANUAL_REVIEW: "result-na"
        }.get(result, "result-na")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def _format_duration(self, milliseconds: int) -> str:
        """Format duration in milliseconds to human readable format"""
        if milliseconds < 1000:
            return f"{milliseconds} ms"
        
        seconds = milliseconds / 1000
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f} minutes"
        
        hours = minutes / 60
        return f"{hours:.1f} hours"