#!/usr/bin/env python3
"""
Test Enhanced PowerShell Generation
Demonstrates the enhanced PowerShell script generation with actual policy implementation
"""

import os
import json
import sys
from pathlib import Path

# Add backend path for imports
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    from deployment.enhanced_powershell_generator import EnhancedPowerShellGenerator
    from deployment.policy_path_researcher import PolicyPathResearcher
    print("✓ Successfully imported enhanced deployment modules")
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import method...")
    try:
        # Alternative import for package structure
        import deployment.enhanced_powershell_generator as eps_gen
        import deployment.policy_path_researcher as ppr
        EnhancedPowerShellGenerator = eps_gen.EnhancedPowerShellGenerator
        PolicyPathResearcher = ppr.PolicyPathResearcher
        print("✓ Successfully imported via alternative method")
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")
        print("Please check that you're running from the backend directory")
        print("Current working directory:", os.getcwd())
        sys.exit(1)

def test_enhanced_generation():
    """Test the enhanced PowerShell generation"""
    
    print("=== Enhanced PowerShell Generation Test ===")
    print()
    
    # Sample CIS policies for testing
    test_policies = [
        {
            "id": "1.1.1",
            "name": "Ensure 'Minimum password age' is set to '1 or more day(s)'",
            "description": "This policy setting determines the minimum amount of time (in days) that a user must keep a password before changing it.",
            "category": "Account Policies/Password Policy",
            "cis_level": 1
        },
        {
            "id": "2.3.1.1",
            "name": "Ensure 'Accounts: Block Microsoft accounts' is set to 'Users can't add or log on with Microsoft accounts'",
            "description": "This policy setting prevents users from adding new Microsoft accounts on this computer.",
            "category": "Local Policies/Security Options",
            "cis_level": 1
        },
        {
            "id": "18.1.1.1",
            "name": "Ensure 'Prevent enabling lock screen camera' is set to 'Enabled'",
            "description": "Disables the lock screen camera toggle switch in PC Settings and prevents a camera from being invoked on the lock screen.",
            "category": "Administrative Templates/Control Panel/Personalization",
            "cis_level": 2
        }
    ]
    
    # Initialize the enhanced generator
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"✓ Gemini API key found: {api_key[:10]}...")
    else:
        print("⚠ No Gemini API key found - using fallback research")
    
    generator = EnhancedPowerShellGenerator(api_key)
    
    print(f"✓ Testing with {len(test_policies)} policies")
    print()
    
    # Generate the enhanced PowerShell script
    print("Generating enhanced PowerShell script...")
    script_content = generator.generate_deployment_script(
        policies=test_policies,
        target_os="Windows 11",
        include_backup=True,
        include_verification=True,
        include_rollback=True
    )
    
    # Save the generated script
    output_file = Path("test_output") / "Enhanced-CIS-Deployment.ps1"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✓ Enhanced PowerShell script generated: {output_file}")
    print(f"✓ Script size: {len(script_content):,} characters")
    print()
    
    # Show script preview
    print("=== Script Preview (First 1000 characters) ===")
    print(script_content[:1000])
    print("...")
    print()
    
    # Show policy research statistics
    stats = generator.researcher.get_policy_statistics()
    print("=== Policy Research Statistics ===")
    print(f"Total policies in database: {stats['total_policies']}")
    print(f"Risk levels: {stats['risk_levels']}")
    print(f"Registry hives: {stats['registry_hives']}")
    print(f"Policies requiring reboot: {stats['requires_reboot']} ({stats['reboot_percentage']:.1f}%)")
    print()
    
    print("=== Test Complete ===")
    print(f"Enhanced PowerShell script saved to: {output_file.absolute()}")
    print("You can now test this script on a Windows system (in a VM recommended)")
    print()
    print("IMPORTANT NOTES:")
    print("- Always test scripts in a non-production environment first")
    print("- The script includes backup and rollback functionality")
    print("- Run as Administrator for full functionality")
    print("- Some policies may require system reboot")

def test_policy_research():
    """Test individual policy research"""
    
    print("=== Policy Research Test ===")
    print()
    
    api_key = os.getenv('GEMINI_API_KEY')
    researcher = PolicyPathResearcher(api_key)
    
    test_policy = {
        "id": "test.policy.1",
        "name": "Ensure Windows Firewall is enabled",
        "description": "Test policy for firewall settings",
        "category": "Windows Firewall"
    }
    
    print(f"Researching policy: {test_policy['name']}")
    result = researcher.research_policy_path(test_policy)
    
    if result.success:
        print("✓ Research successful!")
        print(f"  Registry Path: {result.policy_path.registry_path}")
        print(f"  Value Name: {result.policy_path.registry_value_name}")
        print(f"  Enabled Value: {result.policy_path.enabled_value}")
        print(f"  Risk Level: {result.policy_path.risk_level}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Sources: {result.sources}")
    else:
        print(f"✗ Research failed: {result.error_message}")

if __name__ == "__main__":
    print("CIS GPO Compliance Tool - Enhanced PowerShell Generation Test")
    print("=" * 60)
    print()
    
    try:
        test_enhanced_generation()
        print()
        test_policy_research()
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("All tests completed successfully! 🎉")