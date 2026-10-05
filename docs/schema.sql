-- Struktur database Toko Bangunan Sinar Jaya (MySQL/MariaDB)
-- Sumber: ekspor toko_sinar_jaya.sql.
-- Tabel yang dipakai analitik: kategori, produk, pelanggan, transaksi, detail_transaksi.
-- Tabel admin, permintaan_harga, dan detail_permintaan_harga milik website toko.

CREATE TABLE admin (
    id_admin  INT PRIMARY KEY AUTO_INCREMENT,
    username  VARCHAR(50)  NOT NULL,
    password  VARCHAR(255) NOT NULL,
    nama      VARCHAR(100) NOT NULL
);

CREATE TABLE kategori (
    id_kategori   INT PRIMARY KEY AUTO_INCREMENT,
    nama_kategori VARCHAR(100) NOT NULL,
    deskripsi     TEXT DEFAULT NULL
);

CREATE TABLE pelanggan (
    id_pelanggan INT PRIMARY KEY AUTO_INCREMENT,
    nama         VARCHAR(100) NOT NULL,
    no_telepon   VARCHAR(20)  DEFAULT NULL,
    email        VARCHAR(100) DEFAULT NULL
);

CREATE TABLE produk (
    id_produk   INT PRIMARY KEY AUTO_INCREMENT,
    id_kategori INT NOT NULL,
    nama_produk VARCHAR(150) NOT NULL,
    deskripsi   VARCHAR(200) NOT NULL,
    spesifikasi VARCHAR(150) NOT NULL,
    harga       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    stok        INT NOT NULL DEFAULT 0,
    foto        VARCHAR(200) NOT NULL,
    FOREIGN KEY (id_kategori) REFERENCES kategori(id_kategori) ON UPDATE CASCADE
);

CREATE TABLE transaksi (
    id_transaksi      INT PRIMARY KEY AUTO_INCREMENT,
    id_pelanggan      INT NOT NULL,
    tanggal_transaksi DATETIME NOT NULL,
    total             DECIMAL(15,2) DEFAULT 0.00,
    status            ENUM('selesai','diproses','dibatalkan') DEFAULT 'selesai',
    FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan)
);

CREATE TABLE detail_transaksi (
    id_detail    INT PRIMARY KEY AUTO_INCREMENT,
    id_transaksi INT NOT NULL,
    id_produk    INT NOT NULL,
    jumlah       INT NOT NULL,
    harga        DECIMAL(15,2) NOT NULL,   -- harga saat transaksi
    subtotal     DECIMAL(15,2) NOT NULL,
    FOREIGN KEY (id_transaksi) REFERENCES transaksi(id_transaksi) ON DELETE CASCADE,
    FOREIGN KEY (id_produk)    REFERENCES produk(id_produk)
);

CREATE TABLE permintaan_harga (
    id_permintaan INT PRIMARY KEY AUTO_INCREMENT,
    id_pelanggan  INT NOT NULL,
    tanggal       DATETIME NOT NULL DEFAULT current_timestamp(),
    catatan       TEXT DEFAULT NULL,
    status        VARCHAR(50) DEFAULT 'Pending',
    FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE detail_permintaan_harga (
    id_detail     INT PRIMARY KEY AUTO_INCREMENT,
    id_permintaan INT NOT NULL,
    id_produk     INT NOT NULL,
    jumlah        INT NOT NULL DEFAULT 1,
    keterangan    TEXT DEFAULT NULL,
    FOREIGN KEY (id_permintaan) REFERENCES permintaan_harga(id_permintaan) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_produk)     REFERENCES produk(id_produk) ON UPDATE CASCADE
);
