/**
 * Drag & Drop File Upload Component
 * Production-grade file upload with validation and progress
 */

import React, { useState, useCallback, useRef } from 'react';
import { Upload, X, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { ProgressBar } from './ProgressBar';

interface DropZoneProps {
    onFilesSelected: (files: File[]) => void;
    accept?: string;
    maxSize?: number; // in bytes
    maxFiles?: number;
    disabled?: boolean;
    className?: string;
}

export const DropZone: React.FC<DropZoneProps> = ({
    onFilesSelected,
    accept = '.pdf,.docx,.pptx,.xlsx,.zip,.txt,.md,.jpg,.png',
    maxSize = 50 * 1024 * 1024, // 50MB default
    maxFiles = 1,
    disabled = false,
    className = '',
}) => {
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const validateFiles = (files: FileList | File[]): { valid: File[]; errors: string[] } => {
        const valid: File[] = [];
        const errors: string[] = [];

        const fileArray = Array.from(files);

        if (fileArray.length > maxFiles) {
            errors.push(`Maximum ${maxFiles} file${maxFiles > 1 ? 's' : ''} allowed`);
            return { valid: fileArray.slice(0, maxFiles), errors };
        }

        for (const file of fileArray) {
            // Check file size
            if (file.size > maxSize) {
                errors.push(`${file.name}: File too large (max ${Math.round(maxSize / (1024 * 1024))}MB)`);
                continue;
            }

            // Check file type
            const extension = '.' + file.name.split('.').pop()?.toLowerCase();
            const acceptedExtensions = accept.split(',').map(ext => ext.trim().toLowerCase());

            if (!acceptedExtensions.includes(extension)) {
                errors.push(`${file.name}: File type not allowed`);
                continue;
            }

            valid.push(file);
        }

        return { valid, errors };
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        if (disabled) return;

        const files = e.dataTransfer.files;
        const { valid, errors } = validateFiles(files);

        if (errors.length > 0) {
            setError(errors.join('; '));
            setTimeout(() => setError(null), 5000);
        }

        if (valid.length > 0) {
            setError(null);
            onFilesSelected(valid);
        }
    }, [disabled, maxFiles, maxSize, accept, onFilesSelected]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (!disabled) {
            setIsDragging(true);
        }
    }, [disabled]);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (!files) return;

        const { valid, errors } = validateFiles(files);

        if (errors.length > 0) {
            setError(errors.join('; '));
            setTimeout(() => setError(null), 5000);
        }

        if (valid.length > 0) {
            setError(null);
            onFilesSelected(valid);
        }

        // Reset input
        e.target.value = '';
    }, [maxFiles, maxSize, accept, onFilesSelected]);

    const openFileDialog = () => {
        if (!disabled && fileInputRef.current) {
            fileInputRef.current.click();
        }
    };

    return (
        <div className={className}>
            <div
                role="button"
                tabIndex={disabled ? -1 : 0}
                aria-disabled={disabled}
                onKeyDown={(e) => {
                    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault()
                        openFileDialog()
                    }
                }}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={openFileDialog}
                className={`
          relative border-2 border-dashed rounded-lg p-6 md:p-8 text-center cursor-pointer
          overflow-hidden w-full
          transition-[border-color,background-color] duration-200 ease-standard
          ${isDragging
                        ? 'border-accent-primary bg-accent-primary/10'
                        : 'border-border-medium hover:border-border-strong'
                    }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept={accept}
                    multiple={maxFiles > 1}
                    onChange={handleFileInput}
                    disabled={disabled}
                />

                <div className="space-y-4 flex flex-col items-center justify-center min-h-[150px]">
                    <div className="flex justify-center">
                        <Upload className={`w-10 h-10 md:w-12 md:h-12 ${isDragging ? 'text-accent-primary' : 'text-text-muted'}`} />
                    </div>

                    <div className="w-full px-2">
                        <p className="text-base md:text-lg font-medium text-text-primary break-words whitespace-normal">
                            {isDragging ? 'Drop your file here' : 'Drag & drop your file here'}
                        </p>
                        <p className="text-xs md:text-sm text-text-secondary mt-2 break-words">
                            or click to browse
                        </p>
                    </div>

                    <div className="text-xs text-text-muted space-y-2 mt-2 w-full px-4">
                        <p className="break-words leading-relaxed">
                            <span className="font-semibold block sm:inline sm:mr-1">Accepted formats:</span>
                            {accept.split(',').map(ext => ext.replace('.', '').toUpperCase()).join(', ')}
                        </p>
                        <p>Maximum size: <span className="font-semibold">{Math.round(maxSize / (1024 * 1024))}MB</span></p>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mt-4 p-4 bg-danger/10 border border-danger/30 rounded-lg flex items-start gap-3" role="alert">
                    <AlertCircle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-danger">{error}</p>
                </div>
            )}
        </div>
    );
};

interface FileUploadWithPreviewProps extends DropZoneProps {
    files: File[];
    onRemoveFile: (index: number) => void;
    uploadProgress?: Record<string, number>;
    uploadStatus?: string;
}

export const FileUploadWithPreview: React.FC<FileUploadWithPreviewProps> = ({
    files,
    onRemoveFile,
    uploadProgress = {},
    uploadStatus,
    ...dropZoneProps
}) => {
    return (
        <div className="space-y-4">
            {files.length === 0 ? (
                <DropZone {...dropZoneProps} />
            ) : (
                <div className="space-y-3">
                    {files.map((file, index) => (
                        <FilePreviewCard
                            key={`${file.name}-${index}`}
                            file={file}
                            progress={uploadProgress[file.name]}
                            status={uploadStatus}
                            onRemove={() => onRemoveFile(index)}
                        />
                    ))}

                    {files.length < (dropZoneProps.maxFiles || 1) && (
                        <DropZone {...dropZoneProps} />
                    )}
                </div>
            )}
        </div>
    );
};

interface FilePreviewCardProps {
    file: File;
    progress?: number;
    status?: string;
    onRemove: () => void;
}

const FilePreviewCard: React.FC<FilePreviewCardProps> = ({ file, progress, status, onRemove }) => {
    const formatSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const isComplete = progress === 100;
    const isUploading = progress !== undefined && progress > 0 && progress < 100;

    return (
        <div className="bg-background-secondary border border-border-subtle rounded-lg p-4">
            <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                    <FileText className="w-10 h-10 text-accent-primary" />
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-text-primary truncate">
                                {file.name}
                            </p>
                            <p className="text-xs text-text-muted mt-1">
                                {formatSize(file.size)}
                            </p>
                        </div>

                        {!isUploading && (
                            <button
                                onClick={onRemove}
                                className="flex-shrink-0 p-1 hover:bg-background-tertiary rounded transition-colors"
                                aria-label="Remove file"
                            >
                                {isComplete ? (
                                    <CheckCircle className="w-5 h-5 text-success" />
                                ) : (
                                    <X className="w-5 h-5 text-text-muted" />
                                )}
                            </button>
                        )}
                    </div>

                    {progress !== undefined && progress > 0 && (
                        <div className="mt-3">
                            <div className="flex justify-between text-xs mb-1">
                                <span className="text-text-muted">
                                    {status || (isComplete ? 'Complete' : 'Uploading...')}
                                </span>
                                <span className="font-medium text-text-secondary tabular-nums">
                                    {Math.round(progress)}%
                                </span>
                            </div>
                            <ProgressBar
                                value={progress}
                                variant={isComplete ? 'success' : 'default'}
                                size="sm"
                                showPercentage={false}
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DropZone;
