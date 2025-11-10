#!/usr/bin/env python3
"""
EU Data Act Compliance Checker - Core Module

This module provides the main compliance checking functionality
for EU Data Act (Regulation 2023/2854) contracts.
"""

from rdflib import Graph, Namespace
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import json

# Define namespaces
DATAACT = Namespace("http://www.semanticweb.org/dataact#")
DPV = Namespace("https://w3c.github.io/dpv/2.2/dpv/#")
ODRL = Namespace("https://www.w3.org/ns/odrl/2/")
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


class ComplianceResult:
    """Represents the result of a compliance check"""
    
    def __init__(self, article_id: str, article_name: str):
        self.article_id = article_id
        self.article_name = article_name
        self.compliant = True
        self.violations = []
        self.execution_time = 0.0
        self.error = None
    
    def add_violation(self, violation: Dict):
        """Add a violation to the result"""
        self.compliant = False
        self.violations.append(violation)
    
    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return {
            'article_id': self.article_id,
            'article_name': self.article_name,
            'compliant': self.compliant,
            'violation_count': len(self.violations),
            'violations': self.violations,
            'execution_time_ms': round(self.execution_time * 1000, 2),
            'error': self.error
        }


class ContractComplianceReport:
    """Represents a complete compliance report for a contract"""
    
    def __init__(self, contract_name: str, contract_path: str):
        self.contract_name = contract_name
        self.contract_path = contract_path
        self.contract_type = None
        self.checks = {}
        self.timestamp = datetime.now()
        self.total_triples = 0
        self.load_error = None
    
    @property
    def overall_compliant(self) -> bool:
        """Check if contract is overall compliant"""
        if self.load_error:
            return False
        return all(
            check.compliant 
            for check in self.checks.values() 
            if not check.error
        )
    
    @property
    def total_violations(self) -> int:
        """Count total violations across all checks"""
        return sum(
            len(check.violations) 
            for check in self.checks.values()
        )
    
    def add_check(self, article_id: str, result: ComplianceResult):
        """Add a check result"""
        self.checks[article_id] = result
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary"""
        return {
            'contract_name': self.contract_name,
            'contract_path': self.contract_path,
            'contract_type': self.contract_type,
            'timestamp': self.timestamp.isoformat(),
            'total_triples': self.total_triples,
            'overall_compliant': self.overall_compliant,
            'total_violations': self.total_violations,
            'checks': {
                article_id: check.to_dict() 
                for article_id, check in self.checks.items()
            },
            'load_error': self.load_error
        }
    
    def to_json(self, indent=2) -> str:
        """Convert report to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


class DataActComplianceChecker:
    """
    Main compliance checker for EU Data Act contracts.
    
    This class loads contracts in RDF/OWL format and checks them
    against applicable Data Act articles using SPARQL queries.
    """
    
    def __init__(self, 
                 base_ontology_path: str = "dataact-ontology.owl",
                 queries_dir: str = "queries"):
        """
        Initialize the compliance checker.
        
        Args:
            base_ontology_path: Path to the base Data Act ontology
            queries_dir: Directory containing SPARQL query files
        """
        self.base_ontology_path = Path(base_ontology_path)
        self.queries_dir = Path(queries_dir)
        
        # Validate paths
        if not self.base_ontology_path.exists():
            raise FileNotFoundError(
                f"Base ontology not found: {self.base_ontology_path}"
            )
        if not self.queries_dir.exists():
            raise FileNotFoundError(
                f"Queries directory not found: {self.queries_dir}"
            )
        
        # Define article mappings
        self.article_mappings = {
            'B2C': [
                ('4.1', 'User Access Rights', 'query-4.1.sparql'),
            ],
            'B2B': [
                ('8.6', 'Trade Secret Exception', 'query-8.6.sparql'),
            ],
            'B2G': [
                ('19.2a', 'Competitive Use Prohibition', 'query-19.2.a.sparql'),
            ]
        }
    
    def load_contract(self, contract_path: str) -> Tuple[Graph, Optional[str]]:
        """
        Load contract and base ontology into RDF graph.
        
        Args:
            contract_path: Path to contract OWL file
            
        Returns:
            Tuple of (graph, error_message)
        """
        g = Graph()
        
        try:
            # Bind namespaces
            g.bind("dataact", DATAACT)
            g.bind("dpv", DPV)
            g.bind("odrl", ODRL)
            g.bind("rdf", RDF)
            g.bind("rdfs", RDFS)
            
            # Load base ontology
            g.parse(str(self.base_ontology_path), format="xml")
            
            # Load contract
            g.parse(contract_path, format="xml")
            
            return g, None
            
        except FileNotFoundError as e:
            return g, f"File not found: {e}"
        except Exception as e:
            return g, f"Error loading contract: {e}"
 
    def detect_contract_type(self, g: Graph, contract_path: Optional[str] = None) -> str:
        """
        Detect contract type (B2C, B2B, B2G) safely, avoiding ontology contamination.
        """
        PREFIX = "PREFIX dataact: <http://www.semanticweb.org/dataact#> "

        # Try pattern detection by filename first
        if contract_path:
            name = Path(contract_path).stem.lower()
            if "b2c" in name:
                return "B2C"
            if "b2b" in name:
                return "B2B"
            if "b2g" in name:
                return "B2G"

        # Fallback: query actual individuals (not class definitions)
        for t, q in [
            ("B2C", "ASK { ?s a dataact:B2CDataSharing . FILTER(isIRI(?s)) }"),
            ("B2B", "ASK { ?s a dataact:B2BDataSharing . FILTER(isIRI(?s)) }"),
            ("B2G", "ASK { ?s a dataact:B2GDataSharing . FILTER(isIRI(?s)) }"),
        ]:
            if g.query(PREFIX + q).askAnswer:
                return t
        return "UNKNOWN"
    
    def execute_check(self, 
                      g: Graph, 
                      article_id: str, 
                      article_name: str,
                      query_file: str) -> ComplianceResult:
        """
        Execute a single compliance check.
        
        Args:
            g: RDF graph with contract
            article_id: Article identifier (e.g., '4.1')
            article_name: Human-readable article name
            query_file: SPARQL query filename
            
        Returns:
            ComplianceResult object
        """
        result = ComplianceResult(article_id, article_name)
        start_time = datetime.now()
        
        try:
            # Load query
            query_path = self.queries_dir / query_file
            if not query_path.exists():
                result.error = f"Query file not found: {query_file}"
                return result
            
            with open(query_path, 'r', encoding='utf-8') as f:
                query = f.read()
            
            # Execute query
            query_results = g.query(query)
            
            # Process results
            for row in query_results:
                violation = {}
                
                # Extract all fields from result row
                for var in query_results.vars:
                    value = getattr(row, str(var), None)
                    if value is not None:
                        violation[str(var)] = str(value)
                
                result.add_violation(violation)
            
        except Exception as e:
            result.error = f"Error executing query: {e}"
        
        finally:
            end_time = datetime.now()
            result.execution_time = (end_time - start_time).total_seconds()
        
        return result
    
    def check_contract(self, 
                       contract_path: str,
                       contract_name: Optional[str] = None) -> ContractComplianceReport:
        """
        Check a single contract for compliance.
        
        Args:
            contract_path: Path to contract OWL file
            contract_name: Optional human-readable name
            
        Returns:
            ContractComplianceReport object
        """
        if contract_name is None:
            contract_name = Path(contract_path).stem
        
        report = ContractComplianceReport(contract_name, contract_path)
        
        # Load contract
        g, error = self.load_contract(contract_path)
        if error:
            report.load_error = error
            return report
        
        report.total_triples = len(g)
        
        # Detect contract type
        contract_type = self.detect_contract_type(g, contract_path)

        report.contract_type = contract_type
        
        if contract_type == 'UNKNOWN':
            report.load_error = "Could not determine contract type (B2C/B2B/B2G)"
            return report
        
        # Get applicable checks for this contract type
        applicable_checks = self.article_mappings.get(contract_type, [])
        
        # Execute each check
        for article_id, article_name, query_file in applicable_checks:
            check_result = self.execute_check(g, article_id, article_name, query_file)
            report.add_check(article_id, check_result)
        
        return report
    
    def check_multiple_contracts(self, 
                                 contract_paths: List[str]) -> List[ContractComplianceReport]:
        """
        Check multiple contracts for compliance.
        
        Args:
            contract_paths: List of paths to contract OWL files
            
        Returns:
            List of ContractComplianceReport objects
        """
        reports = []
        
        for contract_path in contract_paths:
            report = self.check_contract(contract_path)
            reports.append(report)
        
        return reports
    
    def check_directory(self, 
                        directory_path: str,
                        pattern: str = "*.owl") -> List[ContractComplianceReport]:
        """
        Check all contracts in a directory.
        
        Args:
            directory_path: Path to directory containing contracts
            pattern: File pattern to match (default: *.owl)
            
        Returns:
            List of ContractComplianceReport objects
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        contract_files = list(directory.glob(pattern))
        
        if not contract_files:
            print(f"⚠️  No contract files found matching '{pattern}' in {directory_path}")
            return []
        
        return self.check_multiple_contracts([str(f) for f in contract_files])


class ComplianceReporter:
    """Generates human-readable compliance reports"""
    
    @staticmethod
    def print_report(report: ContractComplianceReport, verbose: bool = False):
        """
        Print a human-readable compliance report.
        
        Args:
            report: ContractComplianceReport to print
            verbose: If True, show detailed violation information
        """
        print("\n" + "=" * 80)
        print(f"COMPLIANCE REPORT: {report.contract_name}")
        print("=" * 80)
        print(f"Contract Path: {report.contract_path}")
        print(f"Contract Type: {report.contract_type}")
        print(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Triples: {report.total_triples:,}")
        
        if report.load_error:
            print(f"\n❌ ERROR: {report.load_error}")
            return
        
        print(f"\n📊 Compliance Status:")
        print(f"   Overall: {'✅ COMPLIANT' if report.overall_compliant else '❌ NON-COMPLIANT'}")
        print(f"   Total Checks: {len(report.checks)}")
        print(f"   Total Violations: {report.total_violations}")
        
        print(f"\n📋 Article Checks:")
        print("-" * 80)
        
        for article_id, check in report.checks.items():
            status_icon = "✅" if check.compliant else "❌"
            status_text = "PASS" if check.compliant else f"FAIL ({len(check.violations)} violations)"
            
            print(f"\n{status_icon} Article {article_id}: {check.article_name}")
            print(f"   Status: {status_text}")
            print(f"   Execution Time: {check.execution_time * 1000:.2f}ms")
            
            if check.error:
                print(f"   ⚠️  Error: {check.error}")
            
            if verbose and check.violations:
                print(f"\n   Violations:")
                for i, violation in enumerate(check.violations, 1):
                    print(f"   [{i}] {violation.get('violationType', 'UNKNOWN')}")
                    print(f"       {violation.get('details', 'No details')}")
                    
                    # Print other fields
                    for key, value in violation.items():
                        if key not in ['violationType', 'details']:
                            print(f"       {key}: {value}")
        
        print("\n" + "=" * 80)
    
    @staticmethod
    def print_summary(reports: List[ContractComplianceReport]):
        """
        Print summary of multiple contract reports.
        
        Args:
            reports: List of ContractComplianceReport objects
        """
        print("\n" + "=" * 80)
        print("COMPLIANCE SUMMARY - ALL CONTRACTS")
        print("=" * 80)
        print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        total_contracts = len(reports)
        compliant_contracts = sum(1 for r in reports if r.overall_compliant)
        total_checks = sum(len(r.checks) for r in reports)
        total_violations = sum(r.total_violations for r in reports)
        
        print(f"📊 Statistics:")
        print(f"   • Total Contracts: {total_contracts}")
        print(f"   • Compliant: {compliant_contracts} ({compliant_contracts/total_contracts*100:.1f}%)")
        print(f"   • Non-Compliant: {total_contracts - compliant_contracts}")
        print(f"   • Total Article Checks: {total_checks}")
        print(f"   • Total Violations: {total_violations}")
        print()
        
        print("📋 Contract Details:")
        print("-" * 80)
        
        for report in reports:
            status_icon = "✅" if report.overall_compliant else "❌"
            print(f"\n{status_icon} {report.contract_name}")
            print(f"   Type: {report.contract_type}")
            print(f"   Violations: {report.total_violations}")
            
            if report.load_error:
                print(f"   ⚠️  Error: {report.load_error}")
            else:
                for article_id, check in report.checks.items():
                    check_status = "✅" if check.compliant else f"❌ ({len(check.violations)})"
                    print(f"      Article {article_id}: {check_status}")
        
        print("\n" + "-" * 80)
        print(f"\n🎯 OVERALL STATUS: ", end="")
        
        if compliant_contracts == total_contracts:
            print("✅ ALL CONTRACTS COMPLIANT")
        else:
            print(f"⚠️  {total_contracts - compliant_contracts} CONTRACT(S) NEED ATTENTION")
        
        print()
    
    @staticmethod
    def export_json(reports: List[ContractComplianceReport], 
                    output_path: str):
        """
        Export reports to JSON file.
        
        Args:
            reports: List of ContractComplianceReport objects
            output_path: Path to output JSON file
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_contracts': len(reports),
            'compliant_contracts': sum(1 for r in reports if r.overall_compliant),
            'total_violations': sum(r.total_violations for r in reports),
            'reports': [r.to_dict() for r in reports]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Report exported to: {output_path}")


if __name__ == "__main__":
    # Quick test
    print("DataAct Compliance Checker - Core Module")
    print("Import this module to use the checker")
