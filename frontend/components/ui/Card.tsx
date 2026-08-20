"use client";

import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  header?: React.ReactNode;
  footer?: React.ReactNode;
}

export function Card({ children, className = "", header, footer }: CardProps) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}>
      {header && (
        <div className="mb-4">
          {header}
        </div>
      )}
      <div>{children}</div>
      {footer && (
        <div className="mt-4">{footer}</div>
      )}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-semibold uppercase tracking-[0.3em] text-slate-500">
          {title}
        </p>
        {subtitle && <p className="mt-1 text-slate-600">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export function CardContent({ children }: { children: React.ReactNode }) {
  return <div>{children}</div>;
}

export function CardFooter({ children }: { children: React.ReactNode }) {
  return <div className="mt-4 flex items-center gap-3">{children}</div>;
}