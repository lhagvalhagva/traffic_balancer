import React from 'react';

interface TabProps {
  children: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
}

export const Tab: React.FC<TabProps> = ({ children, isActive, onClick }) => {
  return (
    <button
      className={`px-6 py-3 text-sm font-medium ${
        isActive 
          ? 'text-blue-600 border-b-2 border-blue-500' 
          : 'text-gray-500 hover:text-gray-700'
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};

export default Tab; 