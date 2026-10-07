import pytest
from utils.logger import get_logger
from flows.e2e_flow import run_payment_e2e_flow
from flows.restitusi_flow import run_restitusi_flow
from helpers.evidence_collector import evidence_collector
from tests.test_all_scenarios import TEST_METADATA

logger = get_logger(__name__)

class TestRestitusiFlow:
    
    @pytest.mark.parametrize("tc_id,plus_days,expect_sanggahan,fake_loan,overcharge,double_submit,is_hold,illegal_dispute,undercharge_confirm, illegal_confirm", [
        pytest.param("TC-49", 30, False, False, False, False, False, False, False, False, id="TC-49"), 
        pytest.param("TC-50", 31, False, False, False, False, False, False, False, False, id="TC-50"), 
        pytest.param("TC-54", 31, True, False, False, False, False, False, False, False, id="TC-54"),  
        pytest.param("TC-56", 30, False, True, False, False, False, False, False, False, id="TC-56"),  
        pytest.param("TC-57", 30, False, False, True, False, False, False, False, False, id="TC-57"),  
        pytest.param("TC-59", 30, False, False, False, False, False, False, True, False, id="TC-59"),  # Konfirmasi lebih rendah
        pytest.param("TC-60", 30, True, False, False, False, False, False, False, False, id="TC-60"),  # Sanggahan Disetujui
        pytest.param("TC-61", 30, False, False, False, False, False, True, False, False, id="TC-61"),  # Sanggahan Ilegal
        pytest.param("TC-62", 30, False, False, False, False, True, False, False, False, id="TC-62"),  # Hold
        pytest.param("TC-63", 30, False, False, False, True, False, False, False, False, id="TC-63"),
        pytest.param("TC-64", 30, False, False, False, False, False, False, False, True, id="TC-64"),  # Konfirmasi Ilegal (Lebih Tinggi)
    ])
    def test_restitusi_flows(self, api_client, db_client, base_payloads, tc_id, plus_days, expect_sanggahan, fake_loan, overcharge, double_submit, is_hold, illegal_dispute, undercharge_confirm, illegal_confirm):
        logger.info(f"=== Starting {tc_id} ===")
        test_steps = "1. Hit Submit Draft hingga Terbit Polis\n2. Mock UDW_POLICY payment_status=1 (kecuali Hold)\n3. Hit API Submit Restitusi\n4. Hit API Konfirmasi Restitusi / Dispute\n5. Validasi Database (Nominal Disetujui)"
        meta = TEST_METADATA.get(tc_id, {})
        tc_name = meta.get("tc_name", f"Flow Restitusi {tc_id}")
        expected_result = meta.get("expected", "Restitusi berhasil diproses sesuai logic")
        precondition = meta.get("precondition", "Polis Terbit")
        test_steps_excel = meta.get("test_steps", test_steps)
        
        evidence_collector.set_test_metadata(tc_id, tc_name=tc_name, expected_result=expected_result, precondition=precondition, test_steps=test_steps_excel)
        
        class DummyEvidenceCollector:
            def add_api_evidence(self, *args, **kwargs): pass
            def add_db_evidence(self, *args, **kwargs): pass
            def add_ui_evidence(self, *args, **kwargs): pass
            def add_email_evidence(self, *args, **kwargs): pass
            def add_epolis_evidence(self, *args, **kwargs): pass
            def set_test_metadata(self, *args, **kwargs): pass
            def set_test_status(self, *args, **kwargs): pass
            
            @property
            def evidences(self):
                from collections import defaultdict
                return defaultdict(lambda: defaultdict(list))
                
        dummy_collector = DummyEvidenceCollector()
        
        logger.info("Executing prerequisites (creating active policy)...")
        prereq_data = run_payment_e2e_flow("TC-30", api_client, db_client, {}, base_payloads, dummy_collector, {}, skip_ui_validation=True)
        import time
        logger.info("Menunggu sinkronisasi status pembayaran (15 detik)...")
        time.sleep(15)
        
        nomor_transaksi = prereq_data["nomor_transaksi"]
        nomor_loan = prereq_data["nomor_loan"]
        policy_no = prereq_data["nomor_sertifikat"]
        premi = prereq_data["premi"]
        tenor = prereq_data["tenor"]
        
        assert nomor_transaksi and nomor_loan and policy_no, "Failed to get prerequisites for Restitusi"
        
        success = run_restitusi_flow(
            api_client=api_client,
            db_client=db_client,
            tc_id=tc_id,
            nomor_transaksi=nomor_transaksi,
            nomor_loan=nomor_loan,
            policy_no=policy_no,
            premi=premi,
            tenor=tenor,
            evidence_collector=evidence_collector,
            plus_days=plus_days,
            expect_sanggahan=expect_sanggahan,
            fake_loan=fake_loan,
            overcharge=overcharge,
            double_submit=double_submit,
            mock_paid_off=not is_hold,
            is_hold=is_hold,
            illegal_dispute=illegal_dispute,
            undercharge_confirm=undercharge_confirm,
            illegal_confirm=illegal_confirm
        )
        
        assert success is True, "Restitusi flow failed"
        logger.info(f"=== {tc_id} Completed Successfully ===")
