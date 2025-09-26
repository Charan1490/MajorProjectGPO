"""
Test script for the PDF parser module
"""

import os
import sys
import json
from pdf_parser import extract_policies_from_pdf

def progress_callback(progress):
    """Display progress during extraction"""
    sys.stdout.write(f"\rExtraction progress: {progress}%")
    sys.stdout.flush()

def main():
    """Main test function"""
    if len(sys.argv) < 2:
        print("Usage: python test_parser.py <path_to_pdf>")
        return
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        return
    
    # Verify file is a PDF
    if not pdf_path.lower().endswith('.pdf'):
        print("Error: File does not appear to be a PDF (must have .pdf extension)")
        return
    
    print(f"Extracting policies from {pdf_path}...")
    
    try:
        policies = extract_policies_from_pdf(pdf_path, progress_callback)
        
        print(f"\nExtracted {len(policies)} policies")
        
        # Save the results to a JSON file
        output_path = "test_output.json"
        with open(output_path, 'w') as f:
            json.dump([p.dict() for p in policies], f, indent=2)
        
        print(f"Results saved to {output_path}")
        
        # Print a sample of the results
        if policies:
            sample_size = min(3, len(policies))
            print(f"\nSample of {sample_size} extracted policies:")
            for i in range(sample_size):
                policy = policies[i]
                print(f"\n{i+1}. {policy.policy_name}")
                print(f"   Category: {policy.category}")
                print(f"   CIS Level: {policy.cis_level}")
                if policy.gpo_path:
                    print(f"   GPO Path: {policy.gpo_path}")
                if policy.registry_path:
                    print(f"   Registry Path: {policy.registry_path}")
    
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()