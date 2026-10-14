"""All failure injection uses temporary fixtures; never company/public inputs."""
import contextlib,copy,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from scripts import build_public_data as build
from scripts import prepare_release as prepare
from scripts import release_write_guard as guard


class PublicBuildRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for name in ['data','pdf','js']:(self.root/name).mkdir()
        (self.root/'js/app.js').write_bytes(b'const APP_CONFIG = {allowCandidateOverrideDisplay:true};\n')
        self.pdf=self.root/'pdf/source.pdf';writer=PdfWriter();writer.add_blank_page(72,72);writer.write(self.pdf)
        self.product={'id':'p-stable','productName':'fixture published','fileName':'source.pdf','pdfPath':'pdf/source.pdf',
                      'issueDate':'2024-01-01','revisionDate':'2024-02-01','signalWord':'경고','hazardStatements':['H315'],'ghsCodes':['GHS07']}
        self.override={'sourcePdfPath':'pdf/source.pdf','sourceRelativePath':'source.pdf','match':{'fileName':'source.pdf'},
                       'revisionDateCandidate':'2024-02-01','signalWordCandidate':'경고','hazardStatements':['H315']}
        self.pp=self.root/'data/msds.public.json';self.po=self.root/'data/msds-overrides.public.json'
        self.lp=self.root/'data/msds.local.json';self.lo=self.root/'data/msds-overrides.local.json'
        published,overrides,_=build.build_public_records([self.product],[self.override],self.root)
        self.write(self.pp,published);self.write(self.po,overrides)
        self.product['productName']='fixture incoming'
        self.write(self.root/'data/release-policy.json',{'expectedProducts':1})
        self.write(self.root/'data/pdf-renames.json',{'renames':{}})
        self.write_sources()
        real_build=build.build_public_records
        self.stack=contextlib.ExitStack()
        self.stack.enter_context(patch.multiple(build,ROOT=self.root,LOCAL_PRODUCTS_PATH=self.lp,LOCAL_OVERRIDES_PATH=self.lo,
                                               PUBLIC_PRODUCTS_PATH=self.pp,PUBLIC_OVERRIDES_PATH=self.po))
        # Supply the fixture root explicitly even for the old main() whose
        # build_public_records default was captured at import time.
        self.stack.enter_context(patch.object(build,'build_public_records',side_effect=lambda p,o,root=None:real_build(p,o,self.root)))
        self.stack.enter_context(patch('scripts.apply_msds_register.RENAMES_PATH',self.root/'data/pdf-renames.json'))
        register_report={'retired':[],'notClassified':[],'ingredientsRestored':0,'missingEntry':[]}
        content_report={'statementsProducts':0,'firstAidFilled':[],'ingredientNames':0,'hazardStatementsFilled':[]}
        self.stack.enter_context(patch.object(build,'apply_register',side_effect=lambda p,o:(p,o,register_report)))
        self.stack.enter_context(patch.object(build,'normalize_content',side_effect=lambda p,o:(p,o,content_report)))

    def tearDown(self):self.stack.close();self.tmp.cleanup()
    def write(self,path,value):path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    def write_sources(self):self.write(self.lp,[self.product]);self.write(self.lo,[self.override])
    def main(self):
        with contextlib.redirect_stdout(io.StringIO()):return build.main()
    def reject_and_preserve(self):
        before=(self.pp.read_bytes(),self.po.read_bytes());rejected=False
        try:rejected=self.main()!=0
        except (OSError,ValueError,RuntimeError,SystemExit):rejected=True
        self.assertTrue(rejected,'Invalid input reported build success')
        self.assertEqual((self.pp.read_bytes(),self.po.read_bytes()),before,'Published files changed after failed build')

    def test_malformed_local_json_preserves_public_pair(self):
        self.lp.write_bytes(b'{broken');self.reject_and_preserve()
    def test_missing_local_input_preserves_public_pair(self):
        self.lp.unlink();self.reject_and_preserve()
    def test_missing_pdf_preserves_public_pair(self):
        self.pdf.unlink();self.reject_and_preserve()
    def test_corrupt_pdf_preserves_public_pair(self):
        self.pdf.write_bytes(b'%PDF-1.4\nBROKEN\n');self.reject_and_preserve()
    def test_failed_extraction_status_cannot_erase_published_candidate(self):
        self.override['extractStatus']='text_extract_failed';self.override['hazardStatements']=[]
        self.write_sources();self.reject_and_preserve()
    def test_failed_orphan_extraction_is_not_published_or_used(self):
        failed={'sourcePdfPath':'pdf/orphan.pdf','match':{'fileName':'orphan.pdf'},'extractStatus':'text_extract_failed'}
        self.write(self.lo,[self.override,failed]);self.assertEqual(self.main(),0)
        self.assertEqual(len(json.loads(self.po.read_bytes())),1)
    def test_invalid_cas_preserves_public_pair(self):
        self.product['ingredients']=[{'chemicalName':'fixture','casNo':'67-64-10','content':'1'}]
        self.write_sources();self.reject_and_preserve()
    def test_invalid_cas_check_digit_preserves_public_pair(self):
        self.product['ingredients']=[{'chemicalName':'fixture','casNo':'67-64-2','content':'1'}]
        self.write_sources();self.reject_and_preserve()
    def test_distinct_source_identifier_and_source_error_remain_allowed(self):
        self.product['ingredients']=[{'chemicalName':'fixture','casNo':'','sourceIdentifier':'KE-12546','content':'1'},
                                    {'chemicalName':'fixture source error','casNo':'','sourceCasNo':'9000-11-07','casSourceIssue':'원문 오류','content':'1'}]
        self.write_sources();self.assertEqual(self.main(),0)
        values=json.loads(self.pp.read_bytes())[0]['ingredients']
        self.assertEqual(values[0]['sourceIdentifier'],'KE-12546');self.assertEqual(values[1]['sourceCasNo'],'9000-11-07')
    def test_changed_id_for_same_pdf_preserves_public_pair(self):
        self.product['id']='different-id';self.write_sources();self.reject_and_preserve()
    def test_missing_product_id_preserves_public_pair(self):
        self.product.pop('id');self.write_sources();self.reject_and_preserve()
    def test_duplicate_product_id_preserves_public_pair(self):
        self.write(self.lp,[self.product,copy.deepcopy(self.product)]);self.reject_and_preserve()
    def test_empty_local_inputs_do_not_blank_existing_public_only_records(self):
        before=(self.pp.read_bytes(),self.po.read_bytes())
        self.write(self.lp,[]);self.write(self.lo,[]);self.assertEqual(self.main(),0)
        self.assertEqual((self.pp.read_bytes(),self.po.read_bytes()),before)
    def test_renamed_pdf_is_resolved_before_missing_file_sanitization(self):
        self.pdf.rename(self.root/'pdf/new.pdf')
        self.write(self.root/'data/pdf-renames.json',{'renames':{'pdf/source.pdf':'pdf/new.pdf'}})
        self.assertEqual(self.main(),0)
        records=json.loads(self.pp.read_bytes());self.assertEqual(len(records),1)
        self.assertEqual(records[0]['id'],'p-stable');self.assertEqual(records[0]['pdfPath'],'pdf/new.pdf')
        self.assertEqual(records[0]['fileName'],'new.pdf')
    def test_renamed_pdf_without_correspondence_preserves_public_pair(self):
        self.pdf.rename(self.root/'pdf/new.pdf');self.reject_and_preserve()
    def test_second_write_failure_restores_first_public_file(self):
        original=build.write_json;calls=0
        def fail_second(path,data):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('simulated write failure')
            return original(path,data)
        with patch.object(build,'write_json',side_effect=fail_second):self.reject_and_preserve()
    def test_valid_update_preserves_product_id_and_pdf_connection(self):
        self.assertEqual(self.main(),0)
        record=json.loads(self.pp.read_bytes())[0]
        self.assertEqual(record['id'],'p-stable');self.assertEqual(record['pdfPath'],'pdf/source.pdf')


class PrepareReleaseRecoveryTests(unittest.TestCase):
    def test_failed_final_manifest_check_restores_manifest_and_public_data(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);(root/'data').mkdir()
            paths=[root/'data/msds.public.json',root/'data/msds-overrides.public.json',root/'data/release-manifest.json']
            for path in paths:path.write_bytes(b'original '+path.name.encode())
            before=[p.read_bytes()for p in paths]
            (root/'data/release-policy.json').write_bytes(b'{"expectedProducts":1}')
            def run(title,*args):
                if title=='배포 목록 다시 만들기':
                    for path in paths:path.write_bytes(b'partial '+path.name.encode())
                if title=='CI 와 같은 검증':raise SystemExit(1)
            with patch.object(prepare,'ROOT',root),patch.object(prepare,'run',side_effect=run),patch('sys.argv',['prepare_release.py','--no-bump']):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):prepare.main()
            self.assertEqual([p.read_bytes()for p in paths],before)
    def test_failed_pipeline_restores_data_manifest_and_asset_files(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);(root/'data').mkdir()
            names=['data/msds.public.json','data/msds-overrides.public.json','data/release-manifest.json',
                   'index.html','guide.html','label.html','register.html','substance.html','sw.js']
            for name in names:(root/name).write_bytes(('before '+name).encode())
            (root/'data/release-policy.json').write_bytes(b'{"expectedProducts":1}')
            before={name:(root/name).read_bytes()for name in names}
            def run(title,*args):
                if title=='테스트':raise SystemExit(1)
                if title=='관리대장 반영':(root/names[0]).write_bytes(b'partial products')
                if title=='문구 꼴·PDF 대조 보완':(root/names[1]).write_bytes(b'partial overrides')
                if title=='화면 판 번호 올리기':
                    for name in names[3:]:(root/name).write_bytes(b'partial version')
            with patch.object(prepare,'ROOT',root),patch.object(prepare,'run',side_effect=run),patch('sys.argv',['prepare_release.py']):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(SystemExit):prepare.main()
            self.assertEqual({name:(root/name).read_bytes()for name in names},before,'Failed release left partial public data or cache version')


class WriteGuardRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.a,self.b=self.root/'a.json',self.root/'b.json';self.a.write_bytes(b'original A');self.b.write_bytes(b'original B')
    def tearDown(self):self.tmp.cleanup()
    def snapshot(self):return self.a.read_bytes(),self.b.read_bytes()
    def test_serialization_failure_cannot_truncate_originals(self):
        before=self.snapshot()
        with self.assertRaises(TypeError):guard.write_json_pair({self.a:{'invalid':set()},self.b:[]})
        self.assertEqual(self.snapshot(),before)
    def test_second_replacement_failure_restores_pair(self):
        before=self.snapshot();real=guard.os.replace;calls=0
        def replace(source,target):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('second replacement denied')
            return real(source,target)
        with patch.object(guard.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):guard.write_json_pair({self.a:['new A'],self.b:['new B']})
        self.assertEqual(self.snapshot(),before)
    def test_failed_initial_pair_removes_only_its_new_outputs(self):
        self.a.unlink();self.b.unlink();real=guard.os.replace;calls=0
        def replace(source,target):
            nonlocal calls
            calls+=1
            if calls==2:raise OSError('second replacement denied')
            return real(source,target)
        with patch.object(guard.os,'replace',side_effect=replace):
            with self.assertRaises(OSError):guard.write_json_pair({self.a:[],self.b:[]})
        self.assertFalse(self.a.exists());self.assertFalse(self.b.exists())
    def test_restore_failure_reports_retained_backup_paths(self):
        before=self.snapshot();real=guard.os.replace;calls=0
        def replace(source,target):
            nonlocal calls
            calls+=1
            if calls>=2:raise OSError('replacement and restore denied')
            return real(source,target)
        with patch.object(guard.os,'replace',side_effect=replace):
            with self.assertRaisesRegex(RuntimeError,'recovery backups kept:'):guard.write_json_pair({self.a:['new A'],self.b:['new B']})
        saved=[p.read_bytes()for p in self.root.glob('*.bak')]
        self.assertIn(before[0],saved);self.assertIn(before[1],saved)
    def test_successful_pair_removes_stages_and_backups(self):
        guard.write_json_pair({self.a:['A'],self.b:['B']})
        self.assertEqual(json.loads(self.a.read_bytes()),['A']);self.assertEqual(json.loads(self.b.read_bytes()),['B'])
        self.assertFalse(list(self.root.glob('.*.msds-*')))


if __name__=='__main__':unittest.main()
