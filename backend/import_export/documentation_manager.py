"""
Documentation Manager for CIS GPO Compliance Tool
Handles documentation import, processing, and association with policies/groups
"""

import os
import hashlib
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import tempfile
import mimetypes

from .models_import_export import (
    DocumentationItem, DocumentationType,
    serialize_documentation_item, deserialize_documentation_item
)

logger = logging.getLogger(__name__)


class DocumentationManager:
    """Manages documentation items and their associations"""
    
    def __init__(self, data_dir: str = "data/documentation"):
        self.data_dir = Path(data_dir)
        self.files_dir = self.data_dir / "files"
        
        # Create directories
        for dir_path in [self.data_dir, self.files_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.documentation_cache: Dict[str, DocumentationItem] = {}
        self._load_documentation_cache()
    
    def _load_documentation_cache(self):
        """Load documentation items from disk"""
        docs_file = self.data_dir / "documentation.json"
        if docs_file.exists():
            try:
                import json
                with open(docs_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for doc_id, doc_data in data.items():
                        self.documentation_cache[doc_id] = deserialize_documentation_item(doc_data)
            except Exception as e:
                logger.error(f"Error loading documentation cache: {e}")
    
    def _save_documentation_cache(self):
        """Save documentation items to disk"""
        docs_file = self.data_dir / "documentation.json"
        try:
            import json
            data = {
                doc_id: serialize_documentation_item(doc)
                for doc_id, doc in self.documentation_cache.items()
            }
            with open(docs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving documentation cache: {e}")
    
    def _calculate_content_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _detect_document_type(self, file_path: str, content: str = None) -> DocumentationType:
        """Detect document type from file extension and content"""
        if not content:
            mime_type, _ = mimetypes.guess_type(file_path)
        else:
            mime_type = None
        
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf' or (mime_type and 'pdf' in mime_type):
            return DocumentationType.PDF
        elif file_ext in ['.md', '.markdown']:
            return DocumentationType.MARKDOWN
        elif file_ext in ['.txt']:
            return DocumentationType.TEXT
        elif file_ext in ['.html', '.htm'] or (mime_type and 'html' in mime_type):
            return DocumentationType.HTML
        elif file_ext in ['.docx', '.doc'] or (mime_type and 'word' in mime_type):
            return DocumentationType.DOCX
        else:
            # Default to text for unknown types
            return DocumentationType.TEXT
    
    def _extract_text_content(self, file_path: str, doc_type: DocumentationType) -> str:
        """Extract text content from various document types"""
        try:
            if doc_type == DocumentationType.PDF:
                return self._extract_pdf_content(file_path)
            elif doc_type == DocumentationType.DOCX:
                return self._extract_docx_content(file_path)
            elif doc_type in [DocumentationType.TEXT, DocumentationType.MARKDOWN, DocumentationType.HTML]:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # Fallback: try to read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Error extracting content from {file_path}: {e}")
            return f"Error reading file: {e}"
    
    def _extract_pdf_content(self, file_path: str) -> str:
        """Extract text content from PDF"""
        try:
            import PyPDF2
            content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content.append(page.extract_text())
            return '\n'.join(content)
        except ImportError:
            return "PDF processing requires PyPDF2. Install with: pip install PyPDF2"
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            return f"Error reading PDF: {e}"
    
    def _extract_docx_content(self, file_path: str) -> str:
        """Extract text content from DOCX"""
        try:
            import docx
            doc = docx.Document(file_path)
            content = []
            for paragraph in doc.paragraphs:
                content.append(paragraph.text)
            return '\n'.join(content)
        except ImportError:
            return "DOCX processing requires python-docx. Install with: pip install python-docx"
        except Exception as e:
            logger.error(f"Error extracting DOCX content: {e}")
            return f"Error reading DOCX: {e}"
    
    def import_documentation_file(self, file_path: str, title: str = None, 
                                associated_policies: List[str] = None,
                                associated_groups: List[str] = None,
                                associated_templates: List[str] = None,
                                tags: List[str] = None) -> str:
        """Import documentation file and create documentation item"""
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate unique ID
        doc_id = str(uuid.uuid4())
        
        # Detect document type
        doc_type = self._detect_document_type(file_path)
        
        # Extract content
        content = self._extract_text_content(file_path, doc_type)
        
        # Get file info
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Use filename as title if not provided
        if not title:
            title = Path(file_path).stem
        
        # Calculate checksum
        checksum = self._calculate_content_checksum(content)
        
        # Copy file to documentation directory
        dest_path = self.files_dir / f"{doc_id}_{file_name}"
        import shutil
        shutil.copy2(file_path, dest_path)
        
        # Create documentation item
        doc_item = DocumentationItem(
            doc_id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            file_name=file_name,
            file_size=file_size,
            associated_policies=associated_policies or [],
            associated_groups=associated_groups or [],
            associated_templates=associated_templates or [],
            tags=tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            checksum=checksum
        )
        
        # Store in cache
        self.documentation_cache[doc_id] = doc_item
        self._save_documentation_cache()
        
        logger.info(f"Documentation imported: {title} ({doc_id})")
        return doc_id
    
    def create_documentation_item(self, title: str, content: str, 
                                doc_type: DocumentationType = DocumentationType.TEXT,
                                associated_policies: List[str] = None,
                                associated_groups: List[str] = None,
                                associated_templates: List[str] = None,
                                tags: List[str] = None) -> str:
        """Create documentation item from provided content"""
        
        doc_id = str(uuid.uuid4())
        checksum = self._calculate_content_checksum(content)
        
        # Create documentation item
        doc_item = DocumentationItem(
            doc_id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            associated_policies=associated_policies or [],
            associated_groups=associated_groups or [],
            associated_templates=associated_templates or [],
            tags=tags or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            checksum=checksum
        )
        
        # Store in cache
        self.documentation_cache[doc_id] = doc_item
        self._save_documentation_cache()
        
        logger.info(f"Documentation created: {title} ({doc_id})")
        return doc_id
    
    def update_documentation_item(self, doc_id: str, title: str = None, 
                                content: str = None,
                                associated_policies: List[str] = None,
                                associated_groups: List[str] = None,
                                associated_templates: List[str] = None,
                                tags: List[str] = None) -> bool:
        """Update existing documentation item"""
        
        if doc_id not in self.documentation_cache:
            return False
        
        doc_item = self.documentation_cache[doc_id]
        
        # Update fields
        if title is not None:
            doc_item.title = title
        if content is not None:
            doc_item.content = content
            doc_item.checksum = self._calculate_content_checksum(content)
        if associated_policies is not None:
            doc_item.associated_policies = associated_policies
        if associated_groups is not None:
            doc_item.associated_groups = associated_groups
        if associated_templates is not None:
            doc_item.associated_templates = associated_templates
        if tags is not None:
            doc_item.tags = tags
        
        doc_item.updated_at = datetime.now()
        
        self._save_documentation_cache()
        
        logger.info(f"Documentation updated: {doc_item.title} ({doc_id})")
        return True
    
    def delete_documentation_item(self, doc_id: str) -> bool:
        """Delete documentation item and associated file"""
        
        if doc_id not in self.documentation_cache:
            return False
        
        doc_item = self.documentation_cache[doc_id]
        
        # Delete associated file if it exists
        if doc_item.file_name:
            file_path = self.files_dir / f"{doc_id}_{doc_item.file_name}"
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
        
        # Remove from cache
        del self.documentation_cache[doc_id]
        self._save_documentation_cache()
        
        logger.info(f"Documentation deleted: {doc_item.title} ({doc_id})")
        return True
    
    def get_documentation_item(self, doc_id: str) -> Optional[DocumentationItem]:
        """Get documentation item by ID"""
        return self.documentation_cache.get(doc_id)
    
    def search_documentation(self, query: str, 
                           associated_with: str = None,
                           doc_type: DocumentationType = None,
                           tags: List[str] = None) -> List[DocumentationItem]:
        """Search documentation items"""
        results = []
        query_lower = query.lower()
        
        for doc in self.documentation_cache.values():
            # Check type filter
            if doc_type and doc.doc_type != doc_type:
                continue
            
            # Check association filter
            if associated_with:
                if not (associated_with in doc.associated_policies or
                       associated_with in doc.associated_groups or
                       associated_with in doc.associated_templates):
                    continue
            
            # Check tags filter
            if tags:
                if not any(tag in doc.tags for tag in tags):
                    continue
            
            # Check text search
            if (query_lower in doc.title.lower() or
                query_lower in doc.content.lower() or
                any(query_lower in tag.lower() for tag in doc.tags)):
                results.append(doc)
        
        # Sort by relevance (title matches first, then content matches)
        def relevance_score(doc):
            score = 0
            if query_lower in doc.title.lower():
                score += 10
            if query_lower in doc.content.lower():
                score += 1
            return score
        
        results.sort(key=relevance_score, reverse=True)
        return results
    
    def get_documentation_by_association(self, associated_id: str, 
                                       association_type: str = "any") -> List[DocumentationItem]:
        """Get documentation associated with a specific ID"""
        results = []
        
        for doc in self.documentation_cache.values():
            is_associated = False
            
            if association_type in ["any", "policy"] and associated_id in doc.associated_policies:
                is_associated = True
            elif association_type in ["any", "group"] and associated_id in doc.associated_groups:
                is_associated = True
            elif association_type in ["any", "template"] and associated_id in doc.associated_templates:
                is_associated = True
            
            if is_associated:
                results.append(doc)
        
        return sorted(results, key=lambda x: x.updated_at or x.created_at or datetime.now(), reverse=True)
    
    def associate_documentation(self, doc_id: str, 
                              policy_ids: List[str] = None,
                              group_ids: List[str] = None,
                              template_ids: List[str] = None) -> bool:
        """Associate documentation with policies, groups, or templates"""
        
        if doc_id not in self.documentation_cache:
            return False
        
        doc_item = self.documentation_cache[doc_id]
        
        if policy_ids:
            for policy_id in policy_ids:
                if policy_id not in doc_item.associated_policies:
                    doc_item.associated_policies.append(policy_id)
        
        if group_ids:
            for group_id in group_ids:
                if group_id not in doc_item.associated_groups:
                    doc_item.associated_groups.append(group_id)
        
        if template_ids:
            for template_id in template_ids:
                if template_id not in doc_item.associated_templates:
                    doc_item.associated_templates.append(template_id)
        
        doc_item.updated_at = datetime.now()
        self._save_documentation_cache()
        
        logger.info(f"Documentation associations updated: {doc_item.title} ({doc_id})")
        return True
    
    def remove_associations(self, doc_id: str,
                          policy_ids: List[str] = None,
                          group_ids: List[str] = None,
                          template_ids: List[str] = None) -> bool:
        """Remove associations from documentation"""
        
        if doc_id not in self.documentation_cache:
            return False
        
        doc_item = self.documentation_cache[doc_id]
        
        if policy_ids:
            for policy_id in policy_ids:
                if policy_id in doc_item.associated_policies:
                    doc_item.associated_policies.remove(policy_id)
        
        if group_ids:
            for group_id in group_ids:
                if group_id in doc_item.associated_groups:
                    doc_item.associated_groups.remove(group_id)
        
        if template_ids:
            for template_id in template_ids:
                if template_id in doc_item.associated_templates:
                    doc_item.associated_templates.remove(template_id)
        
        doc_item.updated_at = datetime.now()
        self._save_documentation_cache()
        
        logger.info(f"Documentation associations removed: {doc_item.title} ({doc_id})")
        return True
    
    def get_documentation_stats(self) -> Dict[str, Any]:
        """Get documentation statistics"""
        total_docs = len(self.documentation_cache)
        
        # Count by type
        type_counts = {}
        for doc in self.documentation_cache.values():
            doc_type = doc.doc_type.value
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        # Count associations
        policy_associations = sum(len(doc.associated_policies) for doc in self.documentation_cache.values())
        group_associations = sum(len(doc.associated_groups) for doc in self.documentation_cache.values())
        template_associations = sum(len(doc.associated_templates) for doc in self.documentation_cache.values())
        
        # Calculate total size
        total_size = sum(doc.file_size or 0 for doc in self.documentation_cache.values())
        
        return {
            "total_documents": total_docs,
            "documents_by_type": type_counts,
            "total_associations": {
                "policies": policy_associations,
                "groups": group_associations,
                "templates": template_associations
            },
            "total_file_size": total_size
        }
    
    def cleanup_orphaned_files(self) -> int:
        """Clean up files that don't have corresponding documentation items"""
        cleaned_count = 0
        
        # Get all documentation file references
        referenced_files = set()
        for doc in self.documentation_cache.values():
            if doc.file_name:
                referenced_files.add(f"{doc.doc_id}_{doc.file_name}")
        
        # Check all files in the files directory
        for file_path in self.files_dir.iterdir():
            if file_path.is_file() and file_path.name not in referenced_files:
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.info(f"Cleaned up orphaned file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Error cleaning file {file_path}: {e}")
        
        return cleaned_count