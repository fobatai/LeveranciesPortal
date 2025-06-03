/*
  Warnings:

  - You are about to drop the `JobsCache` table. If the table is not empty, all the data it contains will be lost.

*/
-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "JobsCache";
PRAGMA foreign_keys=on;

-- CreateTable
CREATE TABLE "Job" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "description" TEXT NOT NULL,
    "recordChangeDate" DATETIME NOT NULL,
    "statusId" TEXT,
    "vendorId" TEXT,
    "klant_id" INTEGER,
    "apparatuur_omschrijving" TEXT,
    "processfunctie_omschrijving" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Job_statusId_fkey" FOREIGN KEY ("statusId") REFERENCES "UltimoProgressStatus" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Job_vendorId_fkey" FOREIGN KEY ("vendorId") REFERENCES "UltimoVendor" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "Job_klant_id_fkey" FOREIGN KEY ("klant_id") REFERENCES "Klant" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "UltimoProgressStatus" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "description" TEXT NOT NULL
);

-- CreateTable
CREATE TABLE "UltimoVendor" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "description" TEXT,
    "emailAddress" TEXT
);

-- CreateTable
CREATE TABLE "UltimoEmployee" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "description" TEXT,
    "emailAddress" TEXT NOT NULL,
    "vendorId" TEXT NOT NULL,
    CONSTRAINT "UltimoEmployee_vendorId_fkey" FOREIGN KEY ("vendorId") REFERENCES "UltimoVendor" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "ErpSystem" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "domain" TEXT NOT NULL,
    "apiKey" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE INDEX "Job_statusId_idx" ON "Job"("statusId");

-- CreateIndex
CREATE INDEX "Job_vendorId_idx" ON "Job"("vendorId");

-- CreateIndex
CREATE INDEX "idx_job_klant_id" ON "Job"("klant_id");

-- CreateIndex
CREATE UNIQUE INDEX "UltimoEmployee_emailAddress_key" ON "UltimoEmployee"("emailAddress");

-- CreateIndex
CREATE UNIQUE INDEX "ErpSystem_name_key" ON "ErpSystem"("name");
