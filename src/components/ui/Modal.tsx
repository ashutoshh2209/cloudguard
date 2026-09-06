import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '../../utils/cn';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, children, className, icon }: ModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <div 
        className="fixed inset-0 bg-canvas/80 z-50 transition-opacity backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className={cn(
        "fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100%-2rem)] max-w-lg bg-surface-1 border border-line rounded-xl z-50 shadow-elev-4 flex flex-col animate-in zoom-in-95 duration-200",
        className
      )}>
        
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-5 border-b border-line">
            <div className="flex items-center gap-3">
              {icon && (
                <div className="w-8 h-8 rounded-lg bg-surface-2 border border-line flex items-center justify-center">
                  {icon}
                </div>
              )}
              <h2 className="text-[16px] font-bold text-content">{title}</h2>
            </div>
            <button 
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded hover:bg-surface-2 text-content-muted hover:text-content transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-9/50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Content */}
        {children}
      </div>
    </>
  );
}
