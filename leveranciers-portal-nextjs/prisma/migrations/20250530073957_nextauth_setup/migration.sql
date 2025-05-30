/*
  Warnings:

  - The primary key for the `User` table will be changed. If it partially fails, the table could be left without primary key constraint.

*/
-- CreateTable
CREATE TABLE "Account" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "userId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "providerAccountId" TEXT NOT NULL,
    "refresh_token" TEXT,
    "access_token" TEXT,
    "expires_at" INTEGER,
    "token_type" TEXT,
    "scope" TEXT,
    "id_token" TEXT,
    "session_state" TEXT,
    CONSTRAINT "Account_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Session" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "sessionToken" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "expires" DATETIME NOT NULL,
    CONSTRAINT "Session_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "VerificationToken" (
    "identifier" TEXT NOT NULL,
    "token" TEXT NOT NULL,
    "expires" DATETIME NOT NULL
);

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_JobsCache" (
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
    CONSTRAINT "JobsCache_klant_id_fkey" FOREIGN KEY ("klant_id") REFERENCES "Klant" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_JobsCache" ("apparatuur_omschrijving", "createdAt", "data", "id", "klant_id", "leverancier_id", "omschrijving", "processfunctie_omschrijving", "updatedAt", "voortgang_status", "wijzigingsdatum") SELECT "apparatuur_omschrijving", "createdAt", "data", "id", "klant_id", "leverancier_id", "omschrijving", "processfunctie_omschrijving", "updatedAt", "voortgang_status", "wijzigingsdatum" FROM "JobsCache";
DROP TABLE "JobsCache";
ALTER TABLE "new_JobsCache" RENAME TO "JobsCache";
CREATE INDEX "JobsCache_klant_id_idx" ON "JobsCache"("klant_id");
CREATE TABLE "new_StatusToewijzing" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "klant_id" INTEGER NOT NULL,
    "van_status" TEXT NOT NULL,
    "naar_status" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "StatusToewijzing_klant_id_fkey" FOREIGN KEY ("klant_id") REFERENCES "Klant" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
INSERT INTO "new_StatusToewijzing" ("createdAt", "id", "klant_id", "naar_status", "updatedAt", "van_status") SELECT "createdAt", "id", "klant_id", "naar_status", "updatedAt", "van_status" FROM "StatusToewijzing";
DROP TABLE "StatusToewijzing";
ALTER TABLE "new_StatusToewijzing" RENAME TO "StatusToewijzing";
CREATE INDEX "StatusToewijzing_klant_id_idx" ON "StatusToewijzing"("klant_id");
CREATE TABLE "new_User" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT,
    "email" TEXT,
    "emailVerified" DATETIME,
    "image" TEXT,
    "password_hash" TEXT,
    "role" TEXT NOT NULL DEFAULT 'SUPPLIER',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);
INSERT INTO "new_User" ("createdAt", "email", "id", "name", "password_hash", "role", "updatedAt") SELECT "createdAt", "email", "id", "name", "password_hash", "role", "updatedAt" FROM "User";
DROP TABLE "User";
ALTER TABLE "new_User" RENAME TO "User";
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;

-- CreateIndex
CREATE INDEX "Account_userId_idx" ON "Account"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "Account_provider_providerAccountId_key" ON "Account"("provider", "providerAccountId");

-- CreateIndex
CREATE UNIQUE INDEX "Session_sessionToken_key" ON "Session"("sessionToken");

-- CreateIndex
CREATE INDEX "Session_userId_idx" ON "Session"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "VerificationToken_token_key" ON "VerificationToken"("token");

-- CreateIndex
CREATE UNIQUE INDEX "VerificationToken_identifier_token_key" ON "VerificationToken"("identifier", "token");
