--- Adjust the file to your needs, then run as mysql client root admin
--- mysql -u root -h my-sql-address -P 3306 -p < install.sql
USE mysql;
CREATE USER IF NOT EXISTS 'pubobot'@'localhost' IDENTIFIED BY 'pubobot-password';
CREATE DATABASE IF NOT EXISTS `pubodb` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON `pubobot`.* TO 'pubodb'@'localhost';
FLUSH PRIVILEGES;
