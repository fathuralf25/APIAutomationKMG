import pytest
from tests.test_all_scenarios import test_dynamic_scenarios as execute_scenario, TEST_METADATA

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Masukkan daftar TC-ID yang ingin kamu uji secara spesifik di sini.
# Pastikan TC-ID tersebut ada di dalam file collections/test_script.xlsx.
SELECTED_TC = [
    "TC-31",
]
# ==============================================================================

@pytest.mark.parametrize("tc_id", SELECTED_TC)
def test_selected_scenarios(tc_id, api_client, db_client, state, base_payloads):
    """
    Test runner khusus untuk menjalankan skenario uji coba secara spesifik.
    Test ini mem-bypass (tidak me-run) seluruh baris Excel, melainkan hanya 
    menjalankan TC yang ada di list SELECTED_TC di atas.
    
    Logika E2E dan validasinya menggunakan fungsi test utama yang sama 
    sehingga tidak ada duplikasi kode, dan report tetap ter-generate dengan rapi.
    """
    if tc_id not in TEST_METADATA:
        pytest.skip(f"TC {tc_id} tidak ditemukan di file Excel (test_script.xlsx).")
        
    # Memanggil logika test yang sama persis dengan main runner
    execute_scenario(tc_id, api_client, db_client, state, base_payloads)
