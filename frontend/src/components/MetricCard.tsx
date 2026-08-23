import { Card } from "primereact/card";

interface MetricCardProps {
  title: string;
  value: number;
  icon: string;
  variant: "blue" | "green" | "red" | "purple";
}

export default function MetricCard({
  title,
  value,
  icon,
  variant,
}: MetricCardProps) {
  return (
    <Card className="metric-card">
      <div className="metric-card-content">
        <div className="metric-card-info">
          <span className="metric-card-title">
            {title}
          </span>

          <span className="metric-card-value">
            {value}
          </span>
        </div>

        <div
          className={`metric-card-icon metric-card-icon-${variant}`}
        >
          <i className={icon} />
        </div>
      </div>
    </Card>
  );
}