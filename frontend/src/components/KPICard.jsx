function KPICard({
    title,
    value,
    subtitle,
    icon: Icon,
    variant = "default",
}) {
    return (
        <div className={`kpi-card ${variant}`}>
            <div className="kpi-header">
                <span>{title}</span>

                <div className="kpi-icon">
                    <Icon size={19} />
                </div>
            </div>

            <div className="kpi-value">
                {value}
            </div>

            <div className="kpi-subtitle">
                {subtitle}
            </div>
        </div>
    );
}

export default KPICard;