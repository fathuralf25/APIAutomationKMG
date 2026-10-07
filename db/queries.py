QUERY_CEK_DRAFT_AKSEPTASI = """
SELECT 
    d.id_debitur, d.cif, d.nama_debitur, d.ktp, d.npwp, d.tempat_lahir,
    d.tanggal_lahir, d.jenis_kelamin, d.alamat_debitur, d.kode_pos,
    d.jenis_pekerjaan AS debitur_jenis_pekerjaan,
    d.status_kepegawaian AS debitur_status_kepegawaian,
    d.no_telepon, d.no_handphone, d.nama_ibu_kandung,

    s.id_sp2k_submission, s.nomor_transaksi, s.status_akseptasi, s.no_aplikasi, s.kode_bank,
    s.kode_uker, s.request_type, s.status_akseptasi, s.id_product,
    s.id_product_group, s.jenis_covering, s.id_askrindo_branch,
    s.id_broker_agent, s.pks_id,
    
    pr.id AS master_product_id_code, pr.nama_product AS master_product_name,
    pr.jenis_kredit AS master_product_jenis, pr.kode_product_external AS master_product_ext,
    
    a.id_akseptasi_askred, a.jenis_pengajuan, a.tanggal_mulai_covering,
    a.tanggal_akhir_covering, a.nilai_pertanggungan, a.premi, a.rate_premi,
    a.id_valuta, a.kurs_valuta, a.biaya_meterai, a.biaya_admin,
    a.jenis_pekerjaan AS akseptasi_jenis_pekerjaan,
    a.status_kepegawaian AS akseptasi_status_kepegawaian,
    a.mekanisme_penyaluran, a.jangka_waktu, a.nomor_rekening_pinjaman,
    a.nomor_perjanjian_kredit, a.tanggal_perjanjian_kredit, a.outstanding,
    a.kolektibilitas, a.suku_bunga_kredit,
  	
    p.id_payment_account, p.nama_bank, p.nomor_rekening, p.nama_pemilik,

    pay.id_pembayaran, pay.id_sp2k_submission AS pembayaran_id_submission, 
    pay.id_payment_account AS pembayaran_id_account     

FROM t_akseptasi_askred a
JOIN m_debitur d ON a.id_debitur = d.id_debitur
JOIN t_sp2k_submission s ON a.id_submission = s.id_sp2k_submission
LEFT JOIN m_product pr ON s.id_product = pr.id
LEFT JOIN t_pembayaran pay ON s.id_sp2k_submission = pay.id_sp2k_submission
LEFT JOIN m_payment_account p ON pay.id_payment_account = p.id_payment_account
WHERE s.nomor_transaksi = %s;
"""

QUERY_CEK_TERBIT_POLIS = """
SELECT 
    -- 1. Informasi Transaksi & Debitur
    s.nomor_transaksi, s.status_akseptasi,
    d.nama_debitur,
    
    -- 2. Kolom dari t_sertifikat
    cert.id_sertifikat,
    cert.no_sertifikat,
    cert.tgl_sertifikat,
    cert.url_download_sertifikat,
    cert.is_polis_sent,
    
    -- 3. Detail Loan & Premi
    a.nomor_perjanjian_kredit AS nomor_loan,
    a.premi

FROM t_sp2k_submission s
JOIN t_akseptasi_askred a 
    ON s.id_sp2k_submission = a.id_submission
JOIN m_debitur d 
    ON a.id_debitur = d.id_debitur
LEFT JOIN t_sertifikat cert 
    ON s.id_sp2k_submission = cert.id_submission
WHERE s.nomor_transaksi = %s;
"""

# ==========================================
# RESTITUSI QUERIES
# ==========================================

# Query to update payment_status in ACS Staging DB (MSSQL) to mock premium payment
QUERY_ACS_UPDATE_PREMIUM_PAIDOFF = """
UPDATE UNDERWRITING.UDW_POLICY 
SET IS_PREMIUM_PAIDOFF = 1 
WHERE POLICY_NO = %s;
"""

# Query to get restitution details from Postgres DB for validation
QUERY_GET_RESTITUSI = """
SELECT 
    a.id_pembayaran,
    a.nominal_pengajuan_mitra,
    a.nominal_kalkulasi_askrindo,
    a.nominal_disetujui,
    a.nominal_bayar, b.status_akseptasi 
FROM t_pembayaran a
JOIN t_sp2k_submission b ON a.id_sp2k_submission = b.id_sp2k_submission 
WHERE b.nomor_transaksi = %s
AND a.transaction_type = 'REFUND';
"""

# Query for Endorsement Detail Validation (e.g. Cancel / Refund)
QUERY_GET_SERTIFIKAT_DTL_ENDORSEMENT = """
SELECT   
    no_aplikasi,
    no_rekening, 
    creation_type,
    no_sertifikat, 
    no_sertifikat_prev, 
    tgl_sertifikat_acs, 
    nama_pejabat, 
    nama_jabatan, 
    no_jurnal
FROM t_sertifikat_dtl 
WHERE no_sertifikat_prev = %s
ORDER BY created_date DESC LIMIT 1;
"""

# Query for Restitusi Validation (based on nomor_loan)
QUERY_VALIDASI_PEMBAYARAN_RESTITUSI = """
SELECT  
b.nomor_rekening_pinjaman as nomor_loan, 
c.nominal_pengajuan_mitra as nilai_pengajuan, 
c.nominal_kalkulasi_askrindo as nilai_hitung_asuransi, 
c.nominal_disetujui as nilai_disetujui, 
e.value as status, 
c.jenis_restitusi as jenis_restitusi, 
c.transaction_type as transaction_type, 
c.ket_transaksi as keterangan, 
c.tanggal_bayar as tanggal_restitusi, 
d.nama_bank as rekening_bank, 
d.nomor_rekening as rekening_nomor, 
d.nama_pemilik as rekening_pemilik, 
c.remarktransaksi as nomor_reff_pembayaran, 
c.nominal_bayar as nominal_pembayaran 
FROM t_sp2k_submission a 
JOIN t_akseptasi_askred b 
ON a.id_sp2k_submission = b.id_submission  
LEFT JOIN t_pembayaran c 
ON a.id_sp2k_submission = c.id_sp2k_submission  
JOIN m_payment_account d 
ON c.id_payment_account = d.id_payment_account 
JOIN m_lookup e 
ON (a.status_akseptasi = e.key_only and e.lookup_group = 'STATUS_AKSEPTASI') 
WHERE b.nomor_rekening_pinjaman = %s 
AND c.transaction_type = 'REFUND';
"""

# Query for Jurnal BK Restitusi Validation
QUERY_CEK_JURNAL_BK_RESTITUSI = """
SELECT 
    a.nomor_transaksi,
    a.status_akseptasi,
    c.no_jurnal_bk,
    c.nominal_disetujui,
    c.nominal_kalkulasi_askrindo,
    c.nominal_pengajuan_mitra
FROM t_sp2k_submission a
JOIN t_pembayaran c 
    ON a.id_sp2k_submission = c.id_sp2k_submission 
WHERE 
    a.nomor_transaksi = %s
    AND c.transaction_type = 'REFUND';
"""

# Query to get a blacklisted ID_NO from ACS Staging
QUERY_GET_BLACKLISTED_KTP = """
SELECT TOP 1 ID_NO 
FROM CUSTOMER.CUS_DEBITUR WITH (NOLOCK) 
WHERE IS_BLACKLIST = 1 AND ID_NO IS NOT NULL AND LEN(ID_NO) = 16 AND ID_NO NOT LIKE '%[^0-9]%' AND ID_NO != '0000000000000000'
GROUP BY ID_NO
HAVING COUNT(*) = 1;
"""

QUERY_FINAL_STATUS_RESTITUSI = """
SELECT 
    a.id_sp2k_submission,
    c.no_jurnal,
    a.nomor_transaksi,
    a.status_akseptasi,
    a.nominal_premi_askrindo,
    a.nominal_premi_bank,
    a.status_proses_restitusi 
FROM t_sp2k_submission a 
JOIN t_sertifikat b ON a.id_sp2k_submission = b.id_submission 
JOIN t_sertifikat_dtl c ON b.sertifikat_id = c.sertifikat_id  
WHERE a.nomor_transaksi = %s
ORDER BY c.created_date DESC;
"""

QUERY_ACS_UPDATE_BLACKLIST = """
UPDATE CUSTOMER.CUS_DEBITUR 
SET IS_BLACKLIST = %d 
WHERE ID_NO = %s;
"""

QUERY_CANCEL_ACTIVE_SUBMISSIONS = """
UPDATE t_sp2k_submission
SET status_akseptasi = '11'
WHERE id_sp2k_submission IN (
    SELECT s.id_sp2k_submission
    FROM t_sp2k_submission s
    JOIN t_akseptasi_askred a ON s.id_sp2k_submission = a.id_submission
    JOIN m_debitur d ON a.id_debitur = d.id_debitur
    WHERE d.ktp = %s AND s.status_akseptasi NOT IN ('9', '11')
);
"""
