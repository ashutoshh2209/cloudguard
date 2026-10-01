import React from 'react';
import { cn } from '../../utils/cn';

interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  className?: string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

export function DataTable<T>({ data, columns, className, onRowClick, emptyMessage = 'No data available' }: DataTableProps<T>) {
  return (
    <div className={cn("w-full overflow-x-auto rounded-lg border border-line bg-surface-1", className)}>
      <table className="w-full text-left text-sm">
        <thead className="bg-surface-2 border-b border-line text-content-muted text-xs uppercase tracking-wider font-semibold">
          <tr>
            {columns.map((col, i) => (
              <th key={i} className={cn("px-4 py-3", col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line text-content">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-content-muted">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((item, rowIndex) => (
              <tr 
                key={rowIndex} 
                className={cn("hover:bg-surface-2 transition-colors", onRowClick && "cursor-pointer group")}
                onClick={() => onRowClick?.(item)}
              >
                {columns.map((col, colIndex) => (
                  <td key={colIndex} className={cn("px-4 py-3", col.className)}>
                    {col.cell ? col.cell(item) : col.accessorKey ? String(item[col.accessorKey]) : null}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
