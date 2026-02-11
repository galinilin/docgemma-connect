"""Test script for DocGemma MCP tools.

Run with: uv run python test_tools.py

Test categories:
- Drug safety: FDA boxed warnings for various medications
- Medical literature: PubMed searches across specialties
- Drug interactions: Common interaction scenarios
- Clinical trials: Various conditions and locations
"""

import asyncio
import time
from dataclasses import dataclass

# Import directly from tools subpackage to avoid loading torch/model
from docgemma.tools.clinical_trials import find_clinical_trials
from docgemma.tools.drug_interactions import check_drug_interactions
from docgemma.tools.drug_safety import check_drug_safety
from docgemma.tools.medical_literature import search_medical_literature
from docgemma.tools.schemas import (
    ClinicalTrialsInput,
    DrugInteractionsInput,
    DrugSafetyInput,
    MedicalLiteratureInput,
)


@dataclass
class TestResult:
    """Result of a single test case."""
    name: str
    passed: bool
    duration: float
    details: str = ""
    error: str = ""


# =============================================================================
# DRUG SAFETY TEST CASES
# =============================================================================
DRUG_SAFETY_CASES = [
    # Drugs with known boxed warnings
    {"name": "Prozac (fluoxetine)", "brand_name": "Prozac", "expect_warning": True},
    {"name": "Warfarin (anticoagulant)", "brand_name": "Warfarin", "expect_warning": True},
    {"name": "Methotrexate (immunosuppressant)", "brand_name": "Methotrexate", "expect_warning": True},
    {"name": "Clozapine (antipsychotic)", "brand_name": "Clozapine", "expect_warning": True},
    {"name": "Isotretinoin (Accutane)", "brand_name": "Accutane", "expect_warning": True},
    {"name": "Ciprofloxacin (fluoroquinolone)", "brand_name": "Cipro", "expect_warning": True},
    {"name": "Fentanyl (opioid)", "brand_name": "Fentanyl", "expect_warning": True},
    {"name": "Rosiglitazone (Avandia)", "brand_name": "Avandia", "expect_warning": True},
    
    # Common medications (may or may not have warnings)
    {"name": "Lipitor (atorvastatin)", "brand_name": "Lipitor", "expect_warning": None},
    {"name": "Metformin (diabetes)", "brand_name": "Metformin", "expect_warning": None},
    {"name": "Lisinopril (ACE inhibitor)", "brand_name": "Lisinopril", "expect_warning": None},
    {"name": "Omeprazole (PPI)", "brand_name": "Prilosec", "expect_warning": None},
    {"name": "Amlodipine (calcium blocker)", "brand_name": "Norvasc", "expect_warning": None},
    {"name": "Gabapentin (anticonvulsant)", "brand_name": "Neurontin", "expect_warning": None},
    
    # Specialty medications
    {"name": "Humira (adalimumab)", "brand_name": "Humira", "expect_warning": True},
    {"name": "Keytruda (pembrolizumab)", "brand_name": "Keytruda", "expect_warning": None},
    {"name": "Ozempic (semaglutide)", "brand_name": "Ozempic", "expect_warning": None},
    {"name": "Eliquis (apixaban)", "brand_name": "Eliquis", "expect_warning": True},
]


async def test_drug_safety():
    """Test the drug safety tool with various medications."""
    print("\n" + "=" * 70)
    print("DRUG SAFETY TESTS (OpenFDA Boxed Warnings)")
    print("=" * 70)
    
    results = []
    for case in DRUG_SAFETY_CASES:
        start = time.perf_counter()
        try:
            result = await check_drug_safety(DrugSafetyInput(brand_name=case["brand_name"]))
            duration = time.perf_counter() - start
            
            # Check result
            has_warning = result.has_warning
            passed = True
            details = ""
            
            if case["expect_warning"] is True and not has_warning:
                passed = False
                details = "Expected warning but none found"
            elif case["expect_warning"] is False and has_warning:
                passed = False
                details = "Did not expect warning but found one"
            
            if has_warning and result.boxed_warning:
                details = f"Warning: {result.boxed_warning[:100]}..."
            elif not has_warning:
                details = "No boxed warning found"
            
            status = "✓" if passed else "✗"
            print(f"  {status} {case['name']}: {'HAS WARNING' if has_warning else 'no warning'} ({duration:.2f}s)")
            
            results.append(TestResult(
                name=case["name"],
                passed=passed,
                duration=duration,
                details=details,
                error=result.error or ""
            ))
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"  ✗ {case['name']}: ERROR - {e}")
            results.append(TestResult(
                name=case["name"],
                passed=False,
                duration=duration,
                error=str(e)
            ))
    
    return results


# =============================================================================
# MEDICAL LITERATURE TEST CASES
# =============================================================================
LITERATURE_CASES = [
    # Clinical guidelines
    {"name": "Diabetes guidelines", "query": "type 2 diabetes treatment guidelines 2024", "min_results": 1},
    {"name": "Hypertension management", "query": "hypertension blood pressure management", "min_results": 1},
    {"name": "Heart failure treatment", "query": "heart failure SGLT2 inhibitor therapy", "min_results": 1},
    
    # Specific conditions
    {"name": "COPD exacerbation", "query": "COPD acute exacerbation management", "min_results": 1},
    {"name": "Rheumatoid arthritis", "query": "rheumatoid arthritis biologic therapy", "min_results": 1},
    {"name": "Parkinson's disease", "query": "Parkinson disease levodopa treatment", "min_results": 1},
    {"name": "Chronic kidney disease", "query": "CKD chronic kidney disease progression", "min_results": 1},
    
    # Drug-specific searches
    {"name": "Metformin efficacy", "query": "metformin glycemic control efficacy", "min_results": 1},
    {"name": "GLP-1 agonists", "query": "GLP-1 receptor agonist cardiovascular outcomes", "min_results": 1},
    {"name": "PCSK9 inhibitors", "query": "PCSK9 inhibitor LDL cholesterol", "min_results": 1},
    
    # Specialty topics
    {"name": "CAR-T therapy", "query": "CAR-T cell therapy lymphoma", "min_results": 1},
    {"name": "mRNA vaccines", "query": "mRNA vaccine COVID-19 efficacy", "min_results": 1},
    {"name": "Alzheimer's treatment", "query": "Alzheimer disease amyloid therapy", "min_results": 1},
    
    # Pediatric/geriatric
    {"name": "Pediatric asthma", "query": "pediatric asthma inhaled corticosteroids", "min_results": 1},
    {"name": "Geriatric polypharmacy", "query": "elderly polypharmacy medication review", "min_results": 1},
    
    # Mental health
    {"name": "Depression treatment", "query": "major depressive disorder SSRI treatment", "min_results": 1},
    {"name": "Anxiety disorders", "query": "generalized anxiety disorder pharmacotherapy", "min_results": 1},
    {"name": "Bipolar disorder", "query": "bipolar disorder mood stabilizer lithium", "min_results": 1},
]


async def test_medical_literature():
    """Test the PubMed search tool with various medical topics."""
    print("\n" + "=" * 70)
    print("MEDICAL LITERATURE TESTS (PubMed Search)")
    print("=" * 70)
    
    results = []
    for case in LITERATURE_CASES:
        start = time.perf_counter()
        try:
            result = await search_medical_literature(
                MedicalLiteratureInput(query=case["query"], max_results=3)
            )
            duration = time.perf_counter() - start
            
            # Check result
            num_articles = len(result.articles)
            passed = num_articles >= case["min_results"]
            
            details = f"Found {result.total_found} total, returned {num_articles}"
            if result.articles:
                details += f" - First: {result.articles[0].title[:50]}..."
            
            status = "✓" if passed else "✗"
            print(f"  {status} {case['name']}: {num_articles} articles ({duration:.2f}s)")
            
            results.append(TestResult(
                name=case["name"],
                passed=passed,
                duration=duration,
                details=details,
                error=result.error or ""
            ))
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"  ✗ {case['name']}: ERROR - {e}")
            results.append(TestResult(
                name=case["name"],
                passed=False,
                duration=duration,
                error=str(e)
            ))
    
    return results


# =============================================================================
# DRUG INTERACTIONS TEST CASES
# =============================================================================
INTERACTION_CASES = [
    # Classic dangerous interactions
    {
        "name": "Warfarin + NSAIDs",
        "drugs": ["warfarin", "ibuprofen"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "Warfarin + Aspirin",
        "drugs": ["warfarin", "aspirin"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "MAOIs + SSRIs",
        "drugs": ["phenelzine", "fluoxetine"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "Methotrexate + NSAIDs",
        "drugs": ["methotrexate", "naproxen"],
        "expect_interaction": True,
        "severity": "high"
    },
    
    # Moderate interactions
    {
        "name": "Statins + Grapefruit",
        "drugs": ["simvastatin", "atorvastatin"],
        "expect_interaction": None,  # These don't interact with each other
        "severity": None
    },
    {
        "name": "ACE + Potassium",
        "drugs": ["lisinopril", "potassium chloride"],
        "expect_interaction": True,
        "severity": "moderate"
    },
    {
        "name": "Digoxin + Amiodarone",
        "drugs": ["digoxin", "amiodarone"],
        "expect_interaction": True,
        "severity": "high"
    },
    
    # Common polypharmacy scenarios
    {
        "name": "Triple whammy (ACE+NSAID+diuretic)",
        "drugs": ["lisinopril", "ibuprofen", "furosemide"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "Diabetes combo",
        "drugs": ["metformin", "glipizide", "sitagliptin"],
        "expect_interaction": None,  # Generally safe combo
        "severity": None
    },
    {
        "name": "Cardiac medications",
        "drugs": ["metoprolol", "amlodipine", "lisinopril"],
        "expect_interaction": None,  # Common safe combo
        "severity": None
    },
    
    # Anticoagulant interactions
    {
        "name": "DOAC + Antiplatelets",
        "drugs": ["apixaban", "clopidogrel"],
        "expect_interaction": True,
        "severity": "moderate"
    },
    {
        "name": "Warfarin + Antibiotics",
        "drugs": ["warfarin", "ciprofloxacin"],
        "expect_interaction": True,
        "severity": "high"
    },
    
    # QT prolongation combos
    {
        "name": "QT prolongers",
        "drugs": ["amiodarone", "azithromycin"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "Antipsychotic + Antibiotic",
        "drugs": ["haloperidol", "levofloxacin"],
        "expect_interaction": True,
        "severity": "high"
    },
    
    # Serotonin syndrome risk
    {
        "name": "SSRI + Tramadol",
        "drugs": ["sertraline", "tramadol"],
        "expect_interaction": True,
        "severity": "high"
    },
    {
        "name": "SSRI + Triptans",
        "drugs": ["fluoxetine", "sumatriptan"],
        "expect_interaction": True,
        "severity": "moderate"
    },
]


async def test_drug_interactions():
    """Test the drug interactions tool with various drug combinations."""
    print("\n" + "=" * 70)
    print("DRUG INTERACTIONS TESTS (RxNav/OpenFDA)")
    print("=" * 70)
    
    results = []
    for case in INTERACTION_CASES:
        start = time.perf_counter()
        try:
            result = await check_drug_interactions(
                DrugInteractionsInput(drugs=case["drugs"])
            )
            duration = time.perf_counter() - start
            
            # Check result
            num_interactions = len(result.interactions)
            has_interaction = num_interactions > 0
            passed = True
            
            if case["expect_interaction"] is True and not has_interaction:
                passed = False
            elif case["expect_interaction"] is False and has_interaction:
                passed = False
            
            details = f"Found {num_interactions} interactions"
            if result.interactions:
                first = result.interactions[0]
                details += f" - {first.severity}: {first.description[:60]}..."
            
            status = "✓" if passed else "✗"
            drugs_str = " + ".join(case["drugs"])
            print(f"  {status} {case['name']}: {num_interactions} interactions ({duration:.2f}s)")
            
            results.append(TestResult(
                name=case["name"],
                passed=passed,
                duration=duration,
                details=details,
                error=result.error or ""
            ))
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"  ✗ {case['name']}: ERROR - {e}")
            results.append(TestResult(
                name=case["name"],
                passed=False,
                duration=duration,
                error=str(e)
            ))
    
    return results


# =============================================================================
# CLINICAL TRIALS TEST CASES
# =============================================================================
CLINICAL_TRIALS_CASES = [
    # Common cancers
    {"name": "Lung cancer (CA)", "condition": "lung cancer", "location": "California", "min_results": 1},
    {"name": "Breast cancer (NY)", "condition": "breast cancer", "location": "New York", "min_results": 1},
    {"name": "Prostate cancer", "condition": "prostate cancer", "location": None, "min_results": 1},
    {"name": "Colorectal cancer", "condition": "colorectal cancer", "location": None, "min_results": 1},
    {"name": "Melanoma", "condition": "melanoma", "location": None, "min_results": 1},
    
    # Chronic conditions
    {"name": "Type 2 diabetes", "condition": "type 2 diabetes", "location": None, "min_results": 1},
    {"name": "Heart failure", "condition": "heart failure", "location": None, "min_results": 1},
    {"name": "COPD", "condition": "chronic obstructive pulmonary disease", "location": None, "min_results": 1},
    {"name": "Rheumatoid arthritis", "condition": "rheumatoid arthritis", "location": None, "min_results": 1},
    {"name": "Crohn's disease", "condition": "Crohn's disease", "location": None, "min_results": 1},
    
    # Neurological
    {"name": "Alzheimer's disease", "condition": "Alzheimer's disease", "location": None, "min_results": 1},
    {"name": "Parkinson's disease", "condition": "Parkinson's disease", "location": None, "min_results": 1},
    {"name": "Multiple sclerosis", "condition": "multiple sclerosis", "location": None, "min_results": 1},
    {"name": "ALS", "condition": "amyotrophic lateral sclerosis", "location": None, "min_results": 1},
    
    # Mental health
    {"name": "Major depression", "condition": "major depressive disorder", "location": None, "min_results": 1},
    {"name": "Schizophrenia", "condition": "schizophrenia", "location": None, "min_results": 1},
    {"name": "PTSD", "condition": "post-traumatic stress disorder", "location": None, "min_results": 1},
    
    # Rare diseases
    {"name": "Cystic fibrosis", "condition": "cystic fibrosis", "location": None, "min_results": 1},
    {"name": "Sickle cell disease", "condition": "sickle cell disease", "location": None, "min_results": 1},
    {"name": "Huntington's disease", "condition": "Huntington's disease", "location": None, "min_results": 0},  # May have fewer trials
    
    # Pediatric
    {"name": "Pediatric leukemia", "condition": "pediatric acute lymphoblastic leukemia", "location": None, "min_results": 0},
    {"name": "Juvenile diabetes", "condition": "type 1 diabetes children", "location": None, "min_results": 0},
    
    # Location-specific
    {"name": "Any cancer (Texas)", "condition": "cancer", "location": "Texas", "min_results": 1},
    {"name": "Any cancer (Boston)", "condition": "cancer", "location": "Boston", "min_results": 1},
    {"name": "Any cancer (UK)", "condition": "cancer", "location": "United Kingdom", "min_results": 0},
]


async def test_clinical_trials():
    """Test the clinical trials search tool with various conditions and locations."""
    print("\n" + "=" * 70)
    print("CLINICAL TRIALS TESTS (ClinicalTrials.gov)")
    print("=" * 70)
    
    results = []
    for case in CLINICAL_TRIALS_CASES:
        start = time.perf_counter()
        try:
            result = await find_clinical_trials(
                ClinicalTrialsInput(condition=case["condition"], location=case["location"])
            )
            duration = time.perf_counter() - start
            
            # Check result
            num_trials = len(result.trials)
            passed = num_trials >= case["min_results"]
            
            details = f"Found {result.total_found} total, returned {num_trials}"
            if result.trials:
                details += f" - First: {result.trials[0].title[:40]}..."
            
            status = "✓" if passed else "✗"
            loc = f" ({case['location']})" if case["location"] else ""
            print(f"  {status} {case['name']}{loc}: {num_trials} trials ({duration:.2f}s)")
            
            results.append(TestResult(
                name=case["name"],
                passed=passed,
                duration=duration,
                details=details,
                error=result.error or ""
            ))
            
        except Exception as e:
            duration = time.perf_counter() - start
            print(f"  ✗ {case['name']}: ERROR - {e}")
            results.append(TestResult(
                name=case["name"],
                passed=False,
                duration=duration,
                error=str(e)
            ))
    
    return results


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================
async def main():
    """Run all tool tests and generate summary report."""
    print("\n" + "=" * 70)
    print("DocGemma MCP Tools - Comprehensive Test Suite")
    print("=" * 70)
    print(f"Testing {len(DRUG_SAFETY_CASES)} drug safety cases")
    print(f"Testing {len(LITERATURE_CASES)} medical literature cases")
    print(f"Testing {len(INTERACTION_CASES)} drug interaction cases")
    print(f"Testing {len(CLINICAL_TRIALS_CASES)} clinical trials cases")
    total_cases = (
        len(DRUG_SAFETY_CASES) + len(LITERATURE_CASES) +
        len(INTERACTION_CASES) + len(CLINICAL_TRIALS_CASES)
    )
    print(f"Total: {total_cases} test cases")
    
    all_results = {}
    total_start = time.perf_counter()
    
    # Run each test category
    all_results["drug_safety"] = await test_drug_safety()
    all_results["literature"] = await test_medical_literature()
    all_results["interactions"] = await test_drug_interactions()
    all_results["clinical_trials"] = await test_clinical_trials()
    
    total_duration = time.perf_counter() - total_start
    
    # Generate summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    grand_total = 0
    grand_passed = 0
    
    for category, results in all_results.items():
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        avg_time = sum(r.duration for r in results) / total if total > 0 else 0
        
        grand_total += total
        grand_passed += passed
        
        status = "✓" if failed == 0 else "✗"
        print(f"  {status} {category}: {passed}/{total} passed (avg {avg_time:.2f}s)")
        
        # Show failures
        failures = [r for r in results if not r.passed]
        for f in failures[:3]:  # Show up to 3 failures per category
            print(f"      - FAILED: {f.name}")
            if f.error:
                print(f"        Error: {f.error[:80]}")
    
    print("-" * 70)
    pass_rate = (grand_passed / grand_total * 100) if grand_total > 0 else 0
    print(f"  TOTAL: {grand_passed}/{grand_total} passed ({pass_rate:.1f}%)")
    print(f"  TIME: {total_duration:.1f}s total")
    print("=" * 70)
    
    # Return exit code
    return 0 if grand_passed == grand_total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
