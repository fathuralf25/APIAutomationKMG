import os
import subprocess

def main():
    print("="*50)
    print("AUTOMATION RUNNER (WITH DYNAMIC REPORT)")
    print("="*50)
    
    print("\nPilih Environment:")
    print("1. Staging")
    print("2. UAT")
    env_choice = input("Masukkan pilihan (1/2) [Default: 1]: ").strip()
    
    if env_choice == "2":
        os.environ["TEST_ENV"] = "uat"
    else:
        os.environ["TEST_ENV"] = "staging"
        
    project_code = input("\nMasukkan Project Code (kosongkan untuk default PRJ-000): ").strip()
    
    while True:
        report_title = input("Masukkan Judul Laporan (kosongkan untuk default, maks 65 karakter): ").strip()
        if len(report_title) > 65:
            print("[WARNING] Judul terlalu panjang (maksimal 65 karakter). Silakan ulangi.")
        else:
            break

    if project_code:
        os.environ["PROJECT_CODE"] = project_code
    if report_title:
        os.environ["REPORT_TITLE"] = report_title
        
    print("\nPilih mode eksekusi:")
    print("1. Run Semua Test Scenarios (Termasuk Restitusi dsb)")
    print("2. Run Selected Test (berdasarkan nomor TC)")
    print("3. Run Regression Pack (45 Core Scenarios dari Test Script)")
    print("4. Quit")
    
    pilihan = input("Masukkan pilihan (1/2/3/4): ").strip().lower()
    
    if pilihan in ["4", "q", "quit", "exit"]:
        print("\n[INFO] Membatalkan eksekusi runner. Keluar dari program...")
        return
    
    pytest_args = ["pytest", "tests/", "-v"]
    
    if pilihan == "2":
        print("\nContoh input: 1, 2, 15 (akan menjalankan TC-1, TC-2, dan TC-15)")
        tc_input = input("Masukkan nomor TC (pisahkan dengan koma): ").strip()
        
        if tc_input:
            # Membersihkan spasi dan mengekstrak angka saja
            tc_numbers = [num.strip() for num in tc_input.split(",") if num.strip().isdigit()]
            
            if tc_numbers:
                # Membuat format keyword argumen: "TC-1] or TC-1-" dsb
                # Tambahan ']' atau '-' untuk memastikan TC-1 tidak ikut nge-run TC-10 dsb
                marker_conditions = []
                for num in tc_numbers:
                    marker_conditions.append(f"TC-{num}]")
                    marker_conditions.append(f"TC-{num}-")
                
                marker_str = " or ".join(marker_conditions)
                pytest_args.extend(["-k", marker_str])
            else:
                print("[WARNING] Format nomor TC tidak valid! Menjalankan semua test...")
                
    elif pilihan == "3":
        core_tcs = [
            2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 19, 20, 
            22, 24, 25, 27, 28, 29, 30, 32, 36, 
            37, 38, 39, 40, 41, 43, 44, 45, # Multi Fasilitas
            49, 50, 54, 56, 57, 58  # Restitusi
        ]
        print(f"\n[INFO] Memuat Optimized Regression Pack ({len(core_tcs)} Core Scenarios)...")
        # Targetkan folder tests/ agar test_restitusi.py juga ikut dieksekusi
        pytest_args = ["pytest", "tests/", "-v"]
        
        # Format keyword untuk menghindari match substring (misal TC-1 tidak ikut me-run TC-10)
        marker_conditions = []
        for num in core_tcs:
            marker_conditions.append(f"TC-{num}]")
            marker_conditions.append(f"TC-{num}-")
            
        marker_str = " or ".join(marker_conditions)
        pytest_args.extend(["-k", marker_str])
        
    print(f"\n[INFO] Mengeksekusi command: {' '.join(pytest_args)}")
    print("-"*50)
    
    # Jalankan pytest
    subprocess.run(pytest_args)

if __name__ == "__main__":
    main()
