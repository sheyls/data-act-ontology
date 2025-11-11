"""
EU Data Act Compliance Checker - Main Script

Automatically run compliance checks on all contract scenarios found in the 'contracts' folder.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Import compliance checker
sys.path.insert(0, str(Path(__file__).parent))
from compliance_checker import DataActComplianceChecker, ComplianceReporter


def main():
    """Main execution function"""

    print("=" * 80)
    print("EU DATA ACT COMPLIANCE CHECKER")
    print("=" * 80)
    print()

    # Base directories
    base_path = "compliance-checks"
    contracts_dir = os.path.join(base_path, "contracts")

    # Initialize checker
    try:
        checker = DataActComplianceChecker(
            base_ontology_path="data_act_ontology.owl",
            queries_dir=os.path.join(base_path, "queries")
        )
        print("✅ Compliance checker initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing checker: {e}")
        return 1

    # Automatically find all OWL contract files
    contracts = []
    for file_name in os.listdir(contracts_dir):
        if file_name.endswith(".owl"):
            contract_path = os.path.join(contracts_dir, file_name)
            contracts.append({
                "path": contract_path,
                "name": file_name.replace(".owl", "").replace("-", " ").title(),
                "description": "Auto-detected contract file"
            })

    if not contracts:
        print("⚠️  No contract files found in the 'contracts' folder.")
        return 0

    print(f"\n📁 Found {len(contracts)} contract scenarios to check\n")

    # Check each contract
    reports = []
    for c in contracts:
        print(f"🔍 Checking: {c['name']}")
        print(f"   Path: {c['path']}")
        print(f"   Description: {c['description']}")
        try:
            report = checker.check_contract(c["path"], c["name"])
            reports.append(report)

            if report.load_error:
                print(f"   ❌ Error: {report.load_error}")
            else:
                status = "✅ COMPLIANT" if report.overall_compliant else "❌ NON-COMPLIANT"
                print(f"   {status} ({report.total_violations} violations)")
        except Exception as e:
            print(f"   ❌ Error checking contract: {e}")
        print()

    # Detailed reports
    print("\n" + "=" * 80)
    print("DETAILED REPORTS")
    print("=" * 80)

    for r in reports:
        ComplianceReporter.print_report(r, verbose=True)

    # Summary
    ComplianceReporter.print_summary(reports)

    # Export JSON
    date = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join(base_path, "compliance-reports")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"compliance-report-{date}.json")

    try:
        ComplianceReporter.export_json(reports, output_file)
        print(f"\n📤 Report exported to: {output_file}")
    except Exception as e:
        print(f"⚠️  Could not export JSON: {e}")

    # Exit code
    all_compliant = all(r.overall_compliant for r in reports if not r.load_error)
    return 0 if all_compliant else 1


if __name__ == "__main__":
    sys.exit(main())
