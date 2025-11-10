#!/usr/bin/env python3
"""
EU Data Act Compliance Checker - Main Script

Run compliance checks on all contract scenarios.
"""

import sys
from pathlib import Path

# Import the compliance checker
sys.path.insert(0, str(Path(__file__).parent))
from compliance_checker import DataActComplianceChecker, ComplianceReporter


def main():
    """Main execution function"""
    
    print("=" * 80)
    print("EU DATA ACT COMPLIANCE CHECKER")
    print("=" * 80)
    print()
    
    # Initialize checker
    try:
        checker = DataActComplianceChecker(
            base_ontology_path="../dataact-ontology.owl",
            queries_dir="queries"
        )
        print("✅ Compliance checker initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing checker: {e}")
        return 1
    
    # Define contracts to check
    contracts = [
        {
            'path': 'compliance-checks/contracts/contract-b2c-charlie.owl',
            'name': 'B2C - Charlie\'s Smart Watch',
            'description': 'Consumer requests access to health data'
        },
        {
            'path': 'compliance-checks/contracts/contract-b2b-robot.owl',
            'name': 'B2B - Industrial Robot Maintenance',
            'description': 'Factory owner authorizes third-party data access'
        },
        {
            'path': 'compliance-checks/contracts/contract-b2g-health.owl',
            'name': 'B2G - Public Health Emergency',
            'description': 'Health authority receives data for emergency response'
        }
    ]
    
    print(f"\n📁 Found {len(contracts)} contract scenarios to check")
    print()
    
    # Check each contract
    reports = []
    for contract_info in contracts:
        contract_path = contract_info['path']
        contract_name = contract_info['name']
        
        print(f"🔍 Checking: {contract_name}")
        print(f"   Path: {contract_path}")
        print(f"   Description: {contract_info['description']}")
        
        try:
            report = checker.check_contract(contract_path, contract_name)
            reports.append(report)
            
            if report.load_error:
                print(f"   ❌ Error: {report.load_error}")
            else:
                status = "✅ COMPLIANT" if report.overall_compliant else "❌ NON-COMPLIANT"
                print(f"   {status} ({report.total_violations} violations)")
        
        except Exception as e:
            print(f"   ❌ Error checking contract: {e}")
        
        print()
    
    # Print detailed reports
    print("\n" + "=" * 80)
    print("DETAILED REPORTS")
    print("=" * 80)
    
    for report in reports:
        ComplianceReporter.print_report(report, verbose=True)
    
    # Print summary
    ComplianceReporter.print_summary(reports)
    
    # Export to JSON
    output_file = "compliance-report.json"
    try:
        ComplianceReporter.export_json(reports, output_file)
    except Exception as e:
        print(f"⚠️  Could not export JSON: {e}")
    
    # Return exit code
    all_compliant = all(r.overall_compliant for r in reports if not r.load_error)
    return 0 if all_compliant else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
