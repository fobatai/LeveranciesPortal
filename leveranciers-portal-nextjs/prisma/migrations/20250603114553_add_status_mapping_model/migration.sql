-- CreateTable
CREATE TABLE "StatusMapping" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "erpSystemId" TEXT NOT NULL,
    "sourceStatusId" TEXT NOT NULL,
    "sourceStatusDescription" TEXT NOT NULL,
    "targetStatusId" TEXT NOT NULL,
    "targetStatusDescription" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "StatusMapping_erpSystemId_fkey" FOREIGN KEY ("erpSystemId") REFERENCES "ErpSystem" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "StatusMapping_erpSystemId_sourceStatusId_key" ON "StatusMapping"("erpSystemId", "sourceStatusId");
