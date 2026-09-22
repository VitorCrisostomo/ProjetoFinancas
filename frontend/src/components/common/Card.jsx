import React from "react";

const Card = ({ title, value, icon, color = '#3b82f6', children, className = '' }) => {
  return (
    <div className={`card ${className}`} style={{ '--card-color': color }}>
      {icon && <div className="card-icon">{icon}</div>}
      {title && <div className="card-title">{title}</div>}
      {value && <div className="card-value">{value}</div>}
      {children}
    </div>
  );
};

export default Card;