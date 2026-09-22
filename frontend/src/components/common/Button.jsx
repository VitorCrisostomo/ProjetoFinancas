const Button = ({ children, onClick, variant = 'primary', size = 'md', disabled = false, type = 'button', className = '' }) => {
  return (
    <button
      type={type}
      className={`btn btn-${variant} btn-${size} ${className}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
};

export default Button;