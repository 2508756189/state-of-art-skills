'use strict';

const { Client } = require('pg');

function parseBool(value) {
  return value === '1' || value === 'true';
}

function coerceCell(value) {
  if (value === null || value === undefined) {
    return '';
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

function printExpanded(rows) {
  rows.forEach((row, index) => {
    console.log(`-[ RECORD ${index + 1} ]------------------------------`);
    Object.entries(row).forEach(([key, value]) => {
      console.log(`${key} | ${coerceCell(value)}`);
    });
  });
}

function printDelimited(fields, rows, tuplesOnly) {
  if (!tuplesOnly) {
    console.log(fields.map((field) => field.name).join('|'));
  }

  rows.forEach((row) => {
    console.log(
      fields
        .map((field) => coerceCell(row[field.name]))
        .join('|')
    );
  });
}

function printTable(fields, rows) {
  const headers = fields.map((field) => field.name);
  const widths = headers.map((header, index) => {
    const cellWidths = rows.map((row) => coerceCell(row[fields[index].name]).length);
    return Math.max(header.length, ...cellWidths, 1);
  });

  const formatLine = (values) =>
    values.map((value, index) => value.padEnd(widths[index], ' ')).join(' | ');

  console.log(formatLine(headers));
  console.log(widths.map((width) => '-'.repeat(width)).join('-+-'));
  rows.forEach((row) => {
    const values = fields.map((field) => coerceCell(row[field.name]));
    console.log(formatLine(values));
  });
}

async function main() {
  const sql = process.env.CODEX_PG_SQL;
  if (!sql) {
    throw new Error('CODEX_PG_SQL is required.');
  }

  const connectionJson = process.env.CODEX_PG_CONNECTION_JSON;
  if (!connectionJson) {
    throw new Error('CODEX_PG_CONNECTION_JSON is required.');
  }

  const connection = JSON.parse(connectionJson);
  const statementTimeoutMs = Number(process.env.CODEX_PG_TIMEOUT_MS || '30000');
  const allowWrite = parseBool(process.env.CODEX_PG_ALLOW_WRITE || 'false');
  const expanded = parseBool(process.env.CODEX_PG_EXPANDED || 'false');
  const tuplesOnly = parseBool(process.env.CODEX_PG_TUPLES_ONLY || 'false');
  const noAlign = parseBool(process.env.CODEX_PG_NO_ALIGN || 'false');

  const client = new Client(connection);
  await client.connect();

  try {
    let result;

    if (allowWrite) {
      if (statementTimeoutMs > 0) {
        await client.query(`set statement_timeout = '${statementTimeoutMs}ms'`);
      }
      result = await client.query(sql);
    } else {
      await client.query('begin');
      await client.query('set transaction read only');
      if (statementTimeoutMs > 0) {
        await client.query(`set local statement_timeout = '${statementTimeoutMs}ms'`);
      }
      result = await client.query(sql);
      await client.query('rollback');
    }

    const rows = result.rows || [];
    const fields = result.fields || [];

    if (rows.length === 0) {
      if (result.command) {
        console.log(result.command);
      }
      return;
    }

    if (expanded) {
      printExpanded(rows);
      return;
    }

    if (tuplesOnly || noAlign) {
      printDelimited(fields, rows, tuplesOnly);
      return;
    }

    printTable(fields, rows);
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
