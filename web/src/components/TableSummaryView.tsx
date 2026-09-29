import React from "react";
import { useDashboardStore } from "../store";

export default function TableSummaryView() {
  const { snapshot } = useDashboardStore();

  if (!snapshot) {
    return <EmptyState message="Load a snapshot to view the data table." />;
  }

  const [sortKey, setSortKey] = React.useState<string>("Time (s)");
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("asc");
  const [filter, setFilter] = React.useState("");

  const columns = snapshot.columns;

  const rows = React.useMemo(() => {
    let rows = [...snapshot.samples];
    if (filter) {
      const f = filter.toLowerCase();
      rows = rows.filter((row) =>
        Object.values(row).some((v) => String(v).toLowerCase().includes(f))
      );
    }
    rows.sort((a, b) => {
      const av = a[sortKey as keyof typeof a];
      const bv = b[sortKey as keyof typeof b];
      if (av === bv) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortDir === "asc" ? (av as number) - (bv as number) : (bv as number) - (av as number);
    });
    return rows;
  }, [snapshot.samples, sortKey, sortDir, filter]);

  return (
    <div className="tab-panel">
      <div className="table-summary">
        <div className="table-summary__header">
          <h3 className="table-summary__title">Table Summary</h3>
          <div className="table-summary__controls">
            <input
              type="text"
              className="table-summary__filter"
              placeholder="Filter rows…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <span className="table-summary__count">{rows.length} / {snapshot.samples.length} rows</span>
          </div>
        </div>
        <div className="table-summary__scroll">
          <table className="table-summary__table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="table-summary__th"
                    onClick={() => {
                      setSortKey((prev) => {
                        if (prev === col) {
                          setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                          return col;
                        }
                        setSortDir("asc");
                        return col;
                      });
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <span className="table-summary__th-content">
                      {col}
                      {sortKey === col && (
                        <span className="table-summary__sort-icon">
                          {sortDir === "asc" ? "▲" : "▼"}
                        </span>
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  className={snapshot.outlier_mask[i] ? "table-summary__row--outlier" : ""}
                >
                  {columns.map((col) => {
                    const val = row[col as keyof typeof row];
                    const isNum = typeof val === "number";
                    return (
                      <td
                        key={col}
                        className="table-summary__td"
                        style={{
                          color: snapshot.outlier_mask[i] && col === "Time (s)" ? "var(--color-critical)" : "var(--color-foreground)",
                        }}
                      >
                        {isNum ? val.toFixed(2) : val}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-summary__legend">
          <span className="table-summary__legend-item table-summary__legend-item--outlier">
            <span></span>
            Outlier (anomalous sample)
          </span>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty-state">
      <p>{message}</p>
    </div>
  );
}
