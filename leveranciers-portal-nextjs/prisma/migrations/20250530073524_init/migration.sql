-- CreateTable
CREATE TABLE "Klant" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "naam" TEXT NOT NULL,
    "domein" TEXT NOT NULL,
    "api_key" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "StatusToewijzing" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "klant_id" INTEGER NOT NULL,
    "van_status" TEXT NOT NULL,
    "naar_status" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "StatusToewijzing_klant_id_fkey" FOREIGN KEY ("klant_id") REFERENCES "Klant" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "JobsCache" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "klant_id" INTEGER NOT NULL,
    "omschrijving" TEXT NOT NULL,
    "apparatuur_omschrijving" TEXT,
    "processfunctie_omschrijving" TEXT,
    "voortgang_status" TEXT NOT NULL,
    "leverancier_id" TEXT,
    "wijzigingsdatum" DATETIME NOT NULL,
    "data" JSONB NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "JobsCache_klant_id_fkey" FOREIGN KEY ("klant_id") REFERENCES "Klant" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Inlogcode" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "aangemaakt_op" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "verloopt_op" DATETIME NOT NULL,
    "gebruikt" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "EmailVerificationCache" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email" TEXT NOT NULL,
    "verified" BOOLEAN NOT NULL,
    "timestamp" DATETIME NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "SyncControl" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "force_sync" BOOLEAN NOT NULL DEFAULT false,
    "last_sync" DATETIME,
    "sync_interval" INTEGER NOT NULL DEFAULT 3600,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "User" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "password_hash" TEXT,
    "role" TEXT NOT NULL DEFAULT 'SUPPLIER',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "Klant_domein_key" ON "Klant"("domein");

-- CreateIndex
CREATE INDEX "StatusToewijzing_klant_id_idx" ON "StatusToewijzing"("klant_id");

-- CreateIndex
CREATE INDEX "JobsCache_klant_id_idx" ON "JobsCache"("klant_id");

-- CreateIndex
CREATE INDEX "Inlogcode_email_idx" ON "Inlogcode"("email");

-- CreateIndex
CREATE INDEX "Inlogcode_code_idx" ON "Inlogcode"("code");

-- CreateIndex
CREATE UNIQUE INDEX "EmailVerificationCache_email_key" ON "EmailVerificationCache"("email");

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");
