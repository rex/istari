import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { StateBlock } from "@/components/ui/StateBlock";
import {
  CURRENCY_LABEL,
  CURRENCY_TONE,
  type SortDirection,
  type SortKey,
  defaultDirection,
  formatMinutes,
  sortRows,
} from "@/lib/comparison";
import { formatRelative } from "@/lib/format";
import type { ComparisonDomain, CourseRow } from "@/lib/types-comparison";
import { courseComparisonQueryOptions } from "@/queries/comparison";

const DASH = String.fromCharCode(0x2014);

interface Sort {
  key: SortKey;
  direction: SortDirection;
}

function SortHeader({
  label,
  title,
  sortKey,
  sort,
  onSort,
  numeric = false,
}: {
  label: string;
  title?: string;
  sortKey: SortKey;
  sort: Sort;
  onSort: (key: SortKey) => void;
  numeric?: boolean;
}) {
  const active = sort.key === sortKey;
  return (
    <th
      aria-sort={active ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
      className={numeric ? "num" : undefined}
      title={title}
    >
      <button type="button" className="table__sort" onClick={() => onSort(sortKey)}>
        {label}
      </button>
    </th>
  );
}

function CourseCells({
  row,
  domains,
  objectivesTotal,
}: {
  row: CourseRow;
  domains: ComparisonDomain[];
  objectivesTotal: number;
}) {
  return (
    <tr>
      <td>
        <Link to="/watch/$course" params={{ course: row.course_slug }}>
          {row.course_title}
        </Link>
        {row.exam_code || row.year ? (
          <span className="small muted">
            {" "}
            {[row.exam_code, row.year].filter(Boolean).join(" · ")}
          </span>
        ) : null}
      </td>
      <td className="num">
        {row.objectives_touched}/{objectivesTotal}
      </td>
      <td>
        <Badge tone={CURRENCY_TONE[row.currency]}>{CURRENCY_LABEL[row.currency]}</Badge>
      </td>
      <td className="num">
        {row.lectures_captioned} of {row.lectures_total}
      </td>
      <td className="num">{formatMinutes(row.minutes_mapped)}</td>
      {domains.map((domain) => {
        const cell = row.domains.find((d) => d.domain_code === domain.code);
        return (
          <td key={domain.code} className="num">
            {cell && cell.objectives_touched > 0 ? (
              <>
                {cell.objectives_touched}/{domain.objectives}
                <br />
                <span className="small muted">{formatMinutes(cell.minutes)}</span>
              </>
            ) : (
              DASH
            )}
          </td>
        );
      })}
      <td className="num">
        {row.lectures_completed}/{row.lectures_total}
      </td>
    </tr>
  );
}

export default function CourseComparisonPage() {
  const view = useQuery(courseComparisonQueryOptions());
  const [sort, setSort] = useState<Sort>({ key: "objectives", direction: "desc" });
  const onSort = (key: SortKey) =>
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : { key, direction: defaultDirection(key) },
    );

  if (view.isPending) return <Spinner label="Comparing courses" />;
  if (view.isError) {
    return <StateBlock tone="error" title="Could not compare courses" body={view.error.message} />;
  }
  const data = view.data;
  const rows = sortRows(data.courses, sort.key, sort.direction);
  const uncaptioned = data.courses.filter((row) => row.lectures_captioned === 0).length;
  const header = { sort, onSort };

  return (
    <div className="stack">
      <div className="page-head">
        <h1>Courses compared</h1>
        <p>
          {data.courses.length} courses on the share for {data.exam_code}: how much of each domain
          their captions cover, in objectives touched and minutes, how current their exam is, and
          what you have watched. Coverage and currency, never a quality score.
        </p>
        <p className="cluster small muted">
          <span>
            {data.indexed_at
              ? `Index built ${formatRelative(data.indexed_at)}`
              : "The lecture index has not been built"}
          </span>
          <Link to="/content/lectures">Lecture mapping</Link>
          <Link to="/watch">Watch</Link>
        </p>
      </div>
      {data.scanning ? (
        <StateBlock
          title="Scanning the share"
          body="The catalog is being read; the rows fill in when the scan ends."
        />
      ) : null}
      {!data.indexed_at ? (
        <StateBlock
          title="Build the lecture index first"
          body="Objectives and minutes come from the index; captions and currency are known already."
        />
      ) : null}
      {uncaptioned > 0 ? (
        <p className="muted small" style={{ margin: 0 }}>
          {uncaptioned} of these courses have no captions, so nothing in them can be mapped or
          measured; they show a dash until a transcript exists.
        </p>
      ) : null}
      <div className="table-wrap">
        <table className="table table--courses">
          <thead>
            <tr>
              <SortHeader label="Course" sortKey="title" {...header} />
              <SortHeader
                label="Objectives"
                title={`Objectives touched, of ${data.objectives_total}`}
                sortKey="objectives"
                numeric
                {...header}
              />
              <SortHeader label="Currency" sortKey="currency" {...header} />
              <SortHeader label="Captions" sortKey="captions" numeric {...header} />
              <SortHeader
                label="Mapped"
                title="Minutes of captioned lecture time mapped to an objective"
                sortKey="minutes"
                numeric
                {...header}
              />
              {data.domains.map((domain) => (
                <SortHeader
                  key={domain.code}
                  label={`D${domain.code}`}
                  title={`${domain.name}: objectives touched of ${domain.objectives}, and minutes`}
                  sortKey={`domain:${domain.code}`}
                  numeric
                  {...header}
                />
              ))}
              <SortHeader label="Watched" sortKey="watched" numeric {...header} />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <CourseCells
                key={row.course_slug}
                row={row}
                domains={data.domains}
                objectivesTotal={data.objectives_total}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
