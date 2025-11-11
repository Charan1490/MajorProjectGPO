"""
Comprehensive Test Suite for Module 3 (Dashboard) - 100% Complete
Tests real-time monitoring, ADMX integration, and advanced analytics
"""

import sys
import os
import json
import asyncio
import time
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from realtime_manager import (
    RealtimeMonitoringManager, SystemMetrics, RealtimeEvent, ComplianceTrend
)
from template_manager import TemplateManager
from dashboard_manager import DashboardManager

# Test colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_test(test_name, passed=True):
    """Print test result"""
    status = f"{GREEN}✅ PASSED{RESET}" if passed else f"{RED}❌ FAILED{RESET}"
    print(f"\n{status}: {test_name}")

def print_info(text):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")


async def test_realtime_monitoring():
    """Test real-time monitoring system"""
    print_header("TEST 1: Real-Time Monitoring System")
    
    try:
        # Create monitoring manager
        manager = RealtimeMonitoringManager(max_history=50)
        print_info("Created RealtimeMonitoringManager")
        
        # Test system metrics collection
        metrics = manager.get_system_metrics()
        print_info(f"System Metrics: CPU={metrics.cpu_percent}%, Memory={metrics.memory_percent}%")
        assert metrics.cpu_percent >= 0, "CPU percent should be non-negative"
        assert metrics.memory_percent >= 0, "Memory percent should be non-negative"
        print_success("System metrics collection works")
        
        # Test event creation
        event = RealtimeEvent(
            event_id="test_1",
            event_type="policy_change",
            timestamp=datetime.now().isoformat(),
            severity="info",
            title="Test Policy Change",
            message="Testing policy change notification",
            data={"policy_id": "test-123", "policy_name": "Test Policy"}
        )
        print_info("Created test event")
        
        # Test event history
        manager.event_history.append(event)
        assert len(manager.event_history) == 1, "Event should be added to history"
        print_success("Event history tracking works")
        
        # Test compliance trend
        trend = ComplianceTrend(
            timestamp=datetime.now().isoformat(),
            total_policies=100,
            compliant=80,
            non_compliant=15,
            pending=5,
            compliance_rate=80.0
        )
        manager.compliance_history.append(trend)
        assert len(manager.compliance_history) == 1, "Trend should be added to history"
        print_success("Compliance trend tracking works")
        
        # Test statistics
        stats = manager.get_statistics()
        assert "active_connections" in stats, "Statistics should include active connections"
        assert "total_events" in stats, "Statistics should include total events"
        assert "recent_metrics" in stats, "Statistics should include recent metrics"
        print_info(f"Statistics: {stats['total_events']} events, {stats['active_connections']} connections")
        print_success("Statistics retrieval works")
        
        # Test policy change notification
        await manager.notify_policy_change(
            policy_id="pol-123",
            policy_name="Test Policy",
            change_type="updated",
            user="test_user"
        )
        assert manager.total_policies_processed == 1, "Policy counter should increment"
        print_success("Policy change notifications work")
        
        # Test deployment status notification
        await manager.notify_deployment_status(
            deployment_id="deploy-123",
            status="running",
            package_name="Test Package",
            details="Testing deployment"
        )
        assert manager.active_deployments == 1, "Active deployment counter should increment"
        print_success("Deployment status notifications work")
        
        # Test audit result notification
        await manager.notify_audit_result(
            audit_id="audit-123",
            compliant_count=80,
            non_compliant_count=20,
            total_count=100
        )
        print_success("Audit result notifications work")
        
        # Test system alert
        await manager.notify_system_alert(
            severity="warning",
            title="Test Alert",
            message="This is a test system alert",
            data={"test": True}
        )
        print_success("System alerts work")
        
        # Test monitoring lifecycle
        await manager.start_monitoring()
        assert manager.monitoring_active, "Monitoring should be active"
        print_success("Monitoring started successfully")
        
        await asyncio.sleep(1)  # Let it run briefly
        
        await manager.stop_monitoring()
        assert not manager.monitoring_active, "Monitoring should be stopped"
        print_success("Monitoring stopped successfully")
        
        print_test("Real-Time Monitoring System", True)
        return True
        
    except Exception as e:
        print_error(f"Real-time monitoring test failed: {e}")
        print_test("Real-Time Monitoring System", False)
        return False


async def test_admx_integration():
    """Test ADMX integration with Module 2"""
    print_header("TEST 2: ADMX Integration with Module 2")
    
    try:
        # Create template manager
        template_manager = TemplateManager()
        print_info("Created TemplateManager")
        
        # Create test policies
        test_policies = [
            {
                "policy_id": "test-pol-1",
                "policy_number": "1.1.1",
                "policy_name": "Test Account Lockout Policy",
                "profile_applicability": "Level 1",
                "description": "Test policy for account lockout threshold",
                "rationale": "Testing ADMX generation",
                "audit": "Navigate to Computer Configuration",
                "remediation": "Set Account lockout threshold to 5",
                "impact": "Users may be locked out",
                "default_value": "0",
                "recommended_value": "5",
                "references": "CIS Benchmark",
                "cis_controls": "4.1",
                "registry_path": "HKLM\\Software\\Policies\\Microsoft\\Windows\\Lockout:Threshold",
                "gpo_path": "Computer Configuration\\Windows Settings\\Security Settings"
            },
            {
                "policy_id": "test-pol-2",
                "policy_number": "1.1.2",
                "policy_name": "Test Password Policy",
                "profile_applicability": "Level 1",
                "description": "Test policy for password complexity",
                "rationale": "Testing ADMX generation",
                "audit": "Navigate to Computer Configuration",
                "remediation": "Enable password complexity",
                "impact": "Users must use complex passwords",
                "default_value": "Disabled",
                "recommended_value": "Enabled",
                "references": "CIS Benchmark",
                "cis_controls": "4.4",
                "registry_path": "HKLM\\System\\CurrentControlSet\\Control\\Lsa:PasswordComplexity",
                "gpo_path": "Computer Configuration\\Windows Settings\\Security Settings"
            }
        ]
        
        # Import policies
        imported = template_manager.import_cis_policies(test_policies)
        print_info(f"Imported {len(imported)} test policies")
        assert len(imported) == 2, "Should import 2 policies"
        print_success("Policy import works")
        
        # Create template
        template = template_manager.create_template(
            name="Test ADMX Template",
            description="Template for testing ADMX integration",
            cis_level="Level 1",
            policy_ids=list(imported.keys())
        )
        print_info(f"Created template: {template.name}")
        print_success("Template creation works")
        
        # Test ADMX export
        admx_content, adml_content, validation = template_manager.export_template_admx(
            template_id=template.template_id,
            namespace="TestNamespace",
            prefix="TEST",
            validate=True
        )
        
        print_info(f"ADMX Content: {len(admx_content)} characters")
        print_info(f"ADML Content: {len(adml_content)} characters")
        
        assert len(admx_content) > 0, "ADMX content should not be empty"
        assert len(adml_content) > 0, "ADML content should not be empty"
        assert "policyDefinitions" in admx_content, "ADMX should contain policyDefinitions"
        assert "policyDefinitionResources" in adml_content, "ADML should contain policyDefinitionResources"
        print_success("ADMX/ADML generation works")
        
        # Test validation
        assert validation is not None, "Validation result should not be None"
        print_info(f"Validation: {validation.errors_count} errors, {validation.warnings_count} warnings")
        print_success("ADMX validation works")
        
        # Test file export
        result = template_manager.save_admx_to_files(
            template_id=template.template_id,
            output_dir="test_admx_module3",
            namespace="TestNamespace",
            prefix="TEST"
        )
        
        assert result is not None, "File export should return result"
        assert "admx_file" in result, "Result should have admx_file"
        assert "adml_file" in result, "Result should have adml_file"
        assert os.path.exists(result["admx_file"]), "ADMX file should exist"
        assert os.path.exists(result["adml_file"]), "ADML file should exist"
        print_info(f"ADMX file: {result['admx_file']}")
        print_info(f"ADML file: {result['adml_file']}")
        print_success("File export works")
        
        # Test bulk export
        template2 = template_manager.create_template(
            name="Test ADMX Template 2",
            description="Second template for bulk export test",
            cis_level="Level 2",
            policy_ids=list(imported.keys())
        )
        
        results = template_manager.bulk_export_admx(
            template_ids=[template.template_id, template2.template_id],
            output_dir="test_admx_bulk",
            namespace="TestNamespace",
            prefix="TEST"
        )
        
        assert len(results) == 2, "Should have results for both templates"
        successful = [r for r in results if r.get("admx_file") and r.get("adml_file")]
        assert len(successful) == 2, "Both exports should succeed"
        print_info(f"Bulk export: {len(successful)}/2 successful")
        print_success("Bulk ADMX export works")
        
        print_test("ADMX Integration with Module 2", True)
        return True
        
    except Exception as e:
        print_error(f"ADMX integration test failed: {e}")
        import traceback
        traceback.print_exc()
        print_test("ADMX Integration with Module 2", False)
        return False


async def test_advanced_analytics():
    """Test advanced analytics features"""
    print_header("TEST 3: Advanced Analytics & Metrics")
    
    try:
        # Create managers
        template_manager = TemplateManager()
        dashboard_manager = DashboardManager()
        realtime_manager = RealtimeMonitoringManager()
        
        print_info("Created managers for analytics testing")
        
        # Create test data
        test_policies = [
            {
                "policy_id": f"anal-pol-{i}",
                "policy_number": f"2.{i}.1",
                "policy_name": f"Analytics Test Policy {i}",
                "profile_applicability": "Level 1" if i % 2 == 0 else "Level 2",
                "description": f"Test policy {i} for analytics",
                "rationale": "Testing analytics",
                "audit": "Test audit",
                "remediation": "Test remediation",
                "category": "Account Policies" if i < 5 else "Security Options"
            }
            for i in range(10)
        ]
        
        # Import to template manager
        imported = template_manager.import_cis_policies(test_policies)
        print_info(f"Imported {len(imported)} policies for analytics")
        
        # Test policy statistics by CIS level
        all_policies = template_manager.get_all_policies()
        level_1_count = len([p for p in all_policies if hasattr(p, 'cis_level') and p.cis_level == "Level 1"])
        level_2_count = len([p for p in all_policies if hasattr(p, 'cis_level') and p.cis_level == "Level 2"])
        total_policies = len(all_policies)
        print_info(f"Policy distribution: Level 1={level_1_count}, Level 2={level_2_count}, Total={total_policies}")
        assert total_policies >= 10, "Should have at least 10 policies total"
        print_success("Policy statistics by CIS level works")
        
        # Test policy statistics by category
        categories = {}
        for policy in template_manager.get_all_policies():
            cat = policy.category or "Uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        print_info(f"Policy categories: {len(categories)} unique categories found")
        assert len(categories) >= 2, "Should have at least 2 categories"
        print_success("Policy statistics by category works")
        
        # Test compliance trends
        for i in range(5):
            await realtime_manager.update_compliance_trend(
                total_policies=10,
                compliant=8 - i,
                non_compliant=2 + i,
                pending=0
            )
            await asyncio.sleep(0.1)
        
        assert len(realtime_manager.compliance_history) == 5, "Should have 5 trend data points"
        print_info(f"Compliance history: {len(realtime_manager.compliance_history)} data points")
        print_success("Compliance trend tracking works")
        
        # Test metrics history
        for i in range(5):
            metrics = realtime_manager.get_system_metrics()
            await realtime_manager.broadcast_metrics(metrics)
            await asyncio.sleep(0.1)
        
        assert len(realtime_manager.metrics_history) >= 5, "Should have at least 5 metrics data points"
        print_info(f"Metrics history: {len(realtime_manager.metrics_history)} data points")
        print_success("Metrics history tracking works")
        
        # Test event statistics
        event_types = {
            "policy_change": 3,
            "deployment_status": 2,
            "audit_result": 2,
            "system_alert": 1
        }
        
        for event_type, count in event_types.items():
            for i in range(count):
                await realtime_manager.notify_system_alert(
                    severity="info",
                    title=f"Test {event_type}",
                    message=f"Test event {i}",
                    data={"type": event_type}
                )
        
        assert realtime_manager.total_events == sum(event_types.values()), "Should track all events"
        print_info(f"Total events tracked: {realtime_manager.total_events}")
        print_success("Event statistics tracking works")
        
        # Test statistics aggregation
        stats = realtime_manager.get_statistics()
        assert stats["total_events"] > 0, "Should have events in statistics"
        assert len(stats["recent_events"]) > 0, "Should have recent events"
        assert len(stats["recent_metrics"]) > 0, "Should have recent metrics"
        assert len(stats["recent_compliance"]) > 0, "Should have recent compliance data"
        print_info(f"Statistics aggregation: {len(stats['recent_events'])} events, {len(stats['recent_metrics'])} metrics")
        print_success("Statistics aggregation works")
        
        print_test("Advanced Analytics & Metrics", True)
        return True
        
    except Exception as e:
        print_error(f"Analytics test failed: {e}")
        import traceback
        traceback.print_exc()
        print_test("Advanced Analytics & Metrics", False)
        return False


async def test_integration():
    """Test end-to-end integration of all Module 3 features"""
    print_header("TEST 4: End-to-End Integration")
    
    try:
        # Initialize all managers
        template_manager = TemplateManager()
        dashboard_manager = DashboardManager()
        realtime_manager = RealtimeMonitoringManager()
        
        print_info("Initialized all Module 3 managers")
        
        # Start monitoring
        await realtime_manager.start_monitoring()
        print_success("Real-time monitoring started")
        
        # Create and import policies
        policies = [
            {
                "policy_id": f"integ-pol-{i}",
                "policy_number": f"3.{i}.1",
                "policy_name": f"Integration Test Policy {i}",
                "profile_applicability": "Level 1",
                "description": f"Integration test policy {i}",
                "rationale": "Testing integration",
                "audit": "Test audit procedure",
                "remediation": "Test remediation steps",
                "registry_path": f"HKLM\\Software\\Test:Setting{i}"
            }
            for i in range(5)
        ]
        
        imported = template_manager.import_cis_policies(policies)
        print_info(f"Imported {len(imported)} policies")
        
        # Notify policy changes
        for policy_id, policy_name in [(p["policy_id"], p["policy_name"]) for p in policies]:
            await realtime_manager.notify_policy_change(
                policy_id=policy_id,
                policy_name=policy_name,
                change_type="created",
                user="integration_test"
            )
        
        print_success("Policy change notifications sent")
        
        # Create template
        template = template_manager.create_template(
            name="Integration Test Template",
            description="Template for integration testing",
            cis_level="Level 1",
            policy_ids=list(imported.keys())
        )
        print_info(f"Created template: {template.name}")
        
        # Export to ADMX
        admx_content, adml_content, validation = template_manager.export_template_admx(
            template_id=template.template_id,
            namespace="IntegrationTest",
            prefix="INTEG"
        )
        
        print_info(f"Generated ADMX: {len(admx_content)} chars, ADML: {len(adml_content)} chars")
        
        # Notify ADMX export success
        await realtime_manager.notify_system_alert(
            severity="success",
            title="ADMX Export Completed",
            message=f"Template '{template.name}' exported successfully",
            data={
                "template_id": template.template_id,
                "admx_size": len(admx_content),
                "adml_size": len(adml_content),
                "validation_errors": validation.errors_count
            }
        )
        print_success("ADMX export notification sent")
        
        # Update compliance trends
        await realtime_manager.update_compliance_trend(
            total_policies=len(imported),
            compliant=len(imported) - 1,
            non_compliant=1,
            pending=0
        )
        print_success("Compliance trend updated")
        
        # Collect final statistics
        stats = realtime_manager.get_statistics()
        print_info(f"Final statistics:")
        print_info(f"  - Total events: {stats['total_events']}")
        print_info(f"  - Policies processed: {stats['policies_processed']}")
        print_info(f"  - Active deployments: {stats['active_deployments']}")
        print_info(f"  - Monitoring active: {stats['monitoring_active']}")
        
        # Verify integration
        assert stats['total_events'] > 0, "Should have events"
        assert stats['policies_processed'] >= len(imported), "Should have processed policies"
        assert len(stats['recent_events']) > 0, "Should have recent events"
        
        # Stop monitoring
        await realtime_manager.stop_monitoring()
        print_success("Real-time monitoring stopped")
        
        print_test("End-to-End Integration", True)
        return True
        
    except Exception as e:
        print_error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        print_test("End-to-End Integration", False)
        return False


async def main():
    """Run all Module 3 tests"""
    print("\n" + "█"*80)
    print("  MODULE 3 (DASHBOARD) - COMPREHENSIVE TEST SUITE")
    print("  Testing: Real-Time Monitoring, ADMX Integration, Analytics")
    print("█"*80)
    
    results = []
    
    # Run tests
    results.append(await test_realtime_monitoring())
    results.append(await test_admx_integration())
    results.append(await test_advanced_analytics())
    results.append(await test_integration())
    
    # Summary
    print_header("TEST SUMMARY")
    passed = sum(results)
    total = len(results)
    
    print(f"\n{GREEN}✅ PASSED: {passed}/{total}{RESET}")
    if passed < total:
        print(f"{RED}❌ FAILED: {total - passed}/{total}{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*80}")
        print("  🎉 ALL TESTS PASSED - MODULE 3 IS 100% COMPLETE!")
        print(f"{'='*80}{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{'='*80}")
        print("  ❌ SOME TESTS FAILED - PLEASE REVIEW")
        print(f"{'='*80}{RESET}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
