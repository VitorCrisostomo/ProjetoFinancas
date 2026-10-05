import { useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { categoryIcons } from '../../utils/category.jsx';

// O menu fica fora da tabela para não ser cortado pela rolagem horizontal.
export default function CategoryPicker({ categories, category, subcategory, onChange,
  label = 'Alterar categoria', disabled = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeName, setActiveName] = useState(category);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 480 });
  const trigger = useRef(null);
  const popup = useRef(null);
  const id = useId();
  const active = categories.find((item) => item.name === activeName);

  useLayoutEffect(() => {
    if (!isOpen) return;
    const rect = trigger.current.getBoundingClientRect();
    const width = Math.min(480, window.innerWidth - 24);
    const height = popup.current.getBoundingClientRect().height;
    const below = rect.bottom + 6;
    const top = below + height <= window.innerHeight - 12 ? below : Math.max(12, rect.top - height - 6);
    setPosition({ top, left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)), width });
    const buttons = popup.current.querySelectorAll('[data-category]');
    const selected = [...buttons].find((button) => button.dataset.category === category);
    (selected || buttons[0])?.focus();

    const handleOutside = (event) => {
      if (!popup.current?.contains(event.target) && !trigger.current?.contains(event.target)) setIsOpen(false);
    };
    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsOpen(false);
        trigger.current?.focus();
      }
    };
    const handleScroll = (event) => {
      if (!popup.current?.contains(event.target)) setIsOpen(false);
    };
    const close = () => setIsOpen(false);
    document.addEventListener('pointerdown', handleOutside);
    document.addEventListener('focusin', handleOutside);
    document.addEventListener('keydown', handleEscape);
    window.addEventListener('resize', close);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('pointerdown', handleOutside);
      document.removeEventListener('focusin', handleOutside);
      document.removeEventListener('keydown', handleEscape);
      window.removeEventListener('resize', close);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [isOpen, category]);

  const choose = (parent, child = null) => {
    setIsOpen(false);
    trigger.current?.focus();
    if (parent.name !== category || (child?.name || null) !== (subcategory || null)) {
      onChange({ category: parent.name, subcategory: child?.name || null });
    }
  };

  const navigate = (event, pane) => {
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const buttons = [...popup.current.querySelectorAll(`[data-pane="${pane}"] button`)];
    const index = buttons.indexOf(event.currentTarget);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1
      : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
    buttons[next]?.focus();
  };

  return (
    <>
      <button ref={trigger} type="button" className="category-picker-trigger" disabled={disabled}
        aria-label={label} aria-haspopup="menu" aria-expanded={isOpen}
        aria-controls={isOpen ? id : undefined}
        onClick={() => { setActiveName(category); setIsOpen(!isOpen); }}
        onKeyDown={(event) => {
          if (event.key === 'ArrowDown') { event.preventDefault(); setActiveName(category); setIsOpen(true); }
        }}>
        <span className="category-picker-value">
          <span>{categoryIcons[category] || '🏷️'} {category || 'Selecionar categoria'}</span>
          {subcategory && <span className="category-picker-child">{subcategory}</span>}
        </span>
        <span aria-hidden="true">▾</span>
      </button>
      {isOpen && createPortal(
        <div ref={popup} id={id} className="category-picker-popup" style={position}>
          <div className="category-picker-pane" data-pane="parents" role="menu" aria-label="Categorias">
            <p className="category-picker-heading">Categorias</p>
            {categories.map((parent) => (
              <button type="button" role="menuitem" key={parent.name} data-category={parent.name}
                className={`category-picker-option${parent.name === activeName ? ' active' : ''}`}
                onMouseEnter={() => setActiveName(parent.name)} onFocus={() => setActiveName(parent.name)}
                onClick={() => choose(parent)}
                onKeyDown={(event) => {
                  navigate(event, 'parents');
                  if (event.key === 'ArrowRight' && parent.subcategories.length) {
                    event.preventDefault();
                    popup.current.querySelector('[data-pane="children"] button')?.focus();
                  }
                }}>
                <span>{categoryIcons[parent.name] || '🏷️'} {parent.name}</span>
                <span aria-hidden="true">{parent.subcategories.length ? '›' : parent.name === category && !subcategory ? '✓' : ''}</span>
              </button>
            ))}
          </div>
          <div className="category-picker-pane category-picker-submenu" data-pane="children"
            role="menu" aria-label={`Subcategorias de ${activeName || 'categoria'}`}>
            <p className="category-picker-heading">{active?.name || 'Subcategorias'}</p>
            {active && <button type="button" role="menuitem" className="category-picker-option"
              onClick={() => choose(active)} onKeyDown={(event) => {
                navigate(event, 'children');
                if (event.key === 'ArrowLeft') {
                  event.preventDefault();
                  [...popup.current.querySelectorAll('[data-category]')]
                    .find((button) => button.dataset.category === active.name)?.focus();
                }
              }}>Sem subcategoria{category === active.name && !subcategory && <span aria-hidden="true">✓</span>}</button>}
            {active?.subcategories.map((child) => (
              <button key={child.name} type="button" role="menuitem" className="category-picker-option"
                onClick={() => choose(active, child)} onKeyDown={(event) => {
                  navigate(event, 'children');
                  if (event.key === 'ArrowLeft') {
                    event.preventDefault();
                    [...popup.current.querySelectorAll('[data-category]')]
                      .find((button) => button.dataset.category === active.name)?.focus();
                  }
                }}>
                <span>{child.name}</span>
                {category === active.name && subcategory === child.name && <span aria-hidden="true">✓</span>}
              </button>
            ))}
            <p className="category-picker-hint">{active?.subcategories.length
              ? 'Escolha uma subcategoria ou use apenas a categoria.'
              : 'Passe sobre outra categoria para ver suas subcategorias.'}</p>
          </div>
        </div>, document.body,
      )}
    </>
  );
}
