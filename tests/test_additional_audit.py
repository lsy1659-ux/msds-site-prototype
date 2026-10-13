import json
import hashlib
from pathlib import Path
import unittest
from scripts.cas_numbers import valid_cas, extract_cas
from scripts.normalize_public_content import normalize_content
from scripts.validate_public_release import ValidationResult, validate_cas_fields
from scripts.extract_pdf_summary import extract_ingredients
from scripts.msds_pdf_text import parse_ingredients

ROOT=Path(__file__).resolve().parents[1]

class AdditionalAuditTests(unittest.TestCase):
    def test_extraction_preserves_t_identifier_and_wrapped_date_without_fake_cas(self):
        source='Polymer 자료없음 T-2023-00604(2028-08-\n30) 1 ~ 6'
        for rows in [extract_ingredients(source),parse_ingredients(source.splitlines(),[])]:
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['casNo'],'')
            self.assertEqual(rows[0]['sourceIdentifier'],'T-2023-00604(2028-08-30)')
            self.assertIn('1',rows[0]['content']);self.assertIn('6',rows[0]['content'])
    def test_release_validation_blocks_false_cas_and_flags_other_identifiers(self):
        result=ValidationResult()
        validate_cas_fields(result,{'ingredients':[{'casNo':'2028-08-3'}]},'sample')
        self.assertEqual(result.errors[0].code,'CAS_NUMBER_INVALID')
        result=ValidationResult()
        validate_cas_fields(result,{'ingredients':[{'casNo':'67-64-10'}]},'sample')
        self.assertEqual(result.warnings[0].code,'CAS_FIELD_NOT_STANDARD')
        result=ValidationResult()
        validate_cas_fields(result,{'ingredients':[{'casNo':'75-28-5, 106-97-8'}]},'sample')
        self.assertEqual(result.issues,[])
    def test_cas_full_token_checksum_and_dates(self):
        for value in ['67-64-1','107-07-3','1330-20-7']:self.assertTrue(valid_cas(value))
        for value in ['2028-08-3','2028-08-30','67-64-10','x67-64-1']:self.assertFalse(valid_cas(value))
        self.assertEqual(extract_cas('T-2023-00604(2028-08-30) 67-64-1 2028-08-3'),['67-64-1'])
        self.assertEqual(extract_cas('x67-64-1 67-64-10'),[])

    def test_repairs_preserve_ingredient_and_original_identifier(self):
        ps=json.loads((ROOT/'data/msds.public.json').read_text(encoding='utf-8'))
        fixes=json.loads((ROOT/'data/msds-content-repairs.json').read_text(encoding='utf-8'))['ingredientIdentifiers']
        for fix in fixes:
            p=next(p for p in ps if p['id']==fix['productId'])
            row=next(r for r in p['ingredients'] if r['chemicalName']==fix['chemicalName'])
            self.assertEqual(row['casNo'],'')
            self.assertEqual(row['sourceIdentifier'],'T-2023-00604(2028-08-30)')
            self.assertEqual(row['content'],'1~6')
            self.assertEqual(hashlib.sha256((ROOT/fix['pdf']).read_bytes()).hexdigest(),fix['sha256'])

    def test_supplier_rebuild_corrects_upstream_candidate_without_guessing(self):
        ps=json.loads((ROOT/'data/msds.public.json').read_text(encoding='utf-8'))
        ovs=json.loads((ROOT/'data/msds-overrides.public.json').read_text(encoding='utf-8'))
        p=next(p for p in ps if p['id']=='msds-pdf-d462ab4576452226')
        o=next(o for o in ovs if o.get('sourcePdfPath')==p['pdfPath'])
        self.assertEqual(p['supplier'],'한일루켐(주)');self.assertEqual(o['supplierCandidate'],'한일루켐(주)')
        p['supplier']=o['supplierCandidate']='나.눈에대한영향:약간의자극을줄수있음.'
        new_ps,new_ovs,_=normalize_content(ps,ovs)
        self.assertEqual(next(p for p in new_ps if p['id']=='msds-pdf-d462ab4576452226')['supplier'],'한일루켐(주)')
        self.assertEqual(next(o for o in new_ovs if o.get('sourcePdfPath')==p['pdfPath'])['supplierCandidate'],'한일루켐(주)')

