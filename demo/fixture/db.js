const pool = require("./pool");

async function insertUser(row) {
  const client = await pool.connect();
  try {
    await client.query(
      "INSERT INTO users (email, name, org_id) VALUES ($1, $2, $3)",
      [row.email, row.name, row.orgId]
    );
  } finally {
    client.release();
  }
}

module.exports = { insertUser };
