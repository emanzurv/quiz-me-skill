const db = require("./db");

async function importUsers(rows) {
  const failed = [];

  rows.forEach(async (row) => {
    try {
      await db.insertUser(row);
    } catch (err) {
      failed.push(row);
    }
  });

  return { imported: rows.length - failed.length, failed };
}

module.exports = { importUsers };
