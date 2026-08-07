import os
import subprocess

def main():
    print("="*50)
    print("AUTOMATION RUNNER (WITH DYNAMIC REPORT)")
    print("="*50)
    
    project_code = input("Masukkan Project Code (kosongkan untuk default PRJ-000): ").strip()
    report_title = input("Masukkan Judul Laporan (kosongkan untuk default): ").strip()

    if project_code:
        os.environ["PROJECT_CODE"] = project_code
    if report_title:
        os.environ["REPORT_TITLE"] = report_title
        
    print("\nPilih mode eksekusi:")
    print("1. Run Semua Test Scenarios")
    print("2. Run Selected Test (berdasarkan nomor TC)")
    
    pilihan = input("Masukkan pilihan (1/2): ").strip()
    
    pytest_args = ["pytest", "tests/test_all_scenarios.py", "-v"]
    
    if pilihan == "2":
        print("\nContoh input: 1, 2, 15 (akan menjalankan TC_1, TC_2, dan TC_15)")
        tc_input = input("Masukkan nomor TC (pisahkan dengan koma): ").strip()
        
        if tc_input:
            # Membersihkan spasi dan mengekstrak angka saja
            tc_numbers = [num.strip() for num in tc_input.split(",") if num.strip().isdigit()]
            
            if tc_numbers:
                # Membuat format argumen marker: "TC_1 or TC_2 or TC_15"
                marker_str = " or ".join([f"TC_{num}" for num in tc_numbers])
                pytest_args.extend(["-m", marker_str])
            else:
                print("[WARNING] Format nomor TC tidak valid! Menjalankan semua test...")
            
    print(f"\n[INFO] Mengeksekusi command: {' '.join(pytest_args)}")
    print("-"*50)
    
    # Jalankan pytest
    subprocess.run(pytest_args)

if __name__ == "__main__":
    main()
