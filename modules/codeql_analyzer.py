import subprocess
import os
import logging
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Set
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodeQLAnalyzer:
    """
    A class to analyze code for security vulnerabilities using CodeQL.
    """
    def __init__(self, code_path: str = None, database_path: str = None, codeql_repo_path: str = None):
        """
        Initialize the CodeQL analyzer.
        
        Args:
            code_path: Path to store code snippets
            database_path: Path to store CodeQL databases
            codeql_repo_path: Path to the CodeQL repository
        """
        # Set environment variable to avoid tokenizers parallelism warning
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        self.code_path = code_path
        self.database_path = database_path
        
        # Use the path from your Jupyter notebook
        self.codeql_repo_path = codeql_repo_path
        
        # Create directories if they don't exist
        os.makedirs(self.code_path, exist_ok=True)
        os.makedirs(self.database_path, exist_ok=True)
        
        logger.info(f"CodeQL analyzer initialized with code_path={self.code_path}, database_path={self.database_path}, codeql_repo_path={self.codeql_repo_path}")
        
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for a language."""
        ext_map = {
            'python': '.py',
            'c': '.c',
            'cpp': '.cpp',
            'java': '.java',
            'javascript': '.js',
            'typescript': '.ts',
            'go': '.go',
            'ruby': '.rb',
            'php': '.php'
        }
        return ext_map.get(language.lower(), '.txt')  
    def _get_codeql_language(self, language: str) -> str:
        """Map language to CodeQL language identifier."""
        lang_map = {
            'python': 'python',
            'c': 'cpp',
            'cpp': 'cpp',
            'java': 'java',
            'javascript': 'javascript',
            'typescript': 'javascript',
            'go': 'go',
            'ruby': 'ruby',
            'php': 'php'
        }
        return lang_map.get(language.lower(), language.lower())

    def save_code_snippet(self, code_snippet: str, language: str, filename: str = 'code_to_analyze') -> str:
        """
        Save a code snippet to a file for analysis.
        
        Args:
            code_snippet: The code to analyze
            language: Programming language ('python', 'c', 'cpp', etc.)
            filename: Base name for the file (without extension)
            
        Returns:
            Path to the saved file
        """
        # Determine file extension based on language
        extension = self._get_file_extension(language)
        
        # Create language-specific directory
        lang_dir = os.path.join(self.code_path, language)
        os.makedirs(lang_dir, exist_ok=True)
        
        # Full path to the file
        file_path = os.path.join(lang_dir, f"{filename}{extension}")
        
        # Remove existing files with the same base name
        for existing_file in os.listdir(lang_dir):
            if existing_file.startswith(filename.split('_')[0]) and existing_file.endswith(extension):
                try:
                    os.remove(os.path.join(lang_dir, existing_file))
                    logger.info(f"Removed existing file: {os.path.join(lang_dir, existing_file)}")
                except Exception as e:
                    logger.warning(f"Failed to remove existing file {existing_file}: {e}")
        
        # Save the code to the file
        with open(file_path, 'w') as file:
            file.write(code_snippet)
        
        logger.info(f"Code saved to: {file_path}")
        return file_path

    
    def create_makefile(self, directory: str) -> None:
        """
        Create a Makefile for C/C++ projects.
        
        Args:
            directory: Directory containing C/C++ files
        """
        # Collect all C/C++ files in the directory
        c_files = [f for f in os.listdir(directory) if f.endswith('.c')]
        cpp_files = [f for f in os.listdir(directory) if f.endswith('.cpp')]
        
        source_files = c_files + cpp_files
        targets = [os.path.splitext(f)[0] for f in source_files]
        
        # Start creating the Makefile content
        makefile_content = ["all: " + ' '.join(targets), ""]
        
        # Add build rules for each target
        for target in targets:
            src_file = next((f for f in source_files if f.startswith(target)), None)
            if src_file:
                compiler = 'gcc' if src_file.endswith('.c') else 'g++'
                makefile_content.append(f"{target}: {src_file}")
                makefile_content.append(f"\t{compiler} {src_file} -o {target}")
                makefile_content.append("")
        
        # Add clean rule
        makefile_content.append("clean:")
        makefile_content.append(f"\trm -f {' '.join(targets)}")
        makefile_content.append("")
        makefile_content.append(".PHONY: all clean")
        
        # Write the Makefile
        with open(os.path.join(directory, 'Makefile'), 'w') as file:
            file.write('\n'.join(makefile_content))
        
        logger.info(f"Makefile created in {directory}")
    
    def create_codeql_database(self, language: str, source_dir: str, db_name: str = None) -> Optional[str]:
        """
        Create a CodeQL database for the specified language and source directory.
        
        Args:
            language: Programming language ('python', 'c', 'cpp', etc.)
            source_dir: Directory containing the source code
            db_name: Name for the database (optional)
            
        Returns:
            Path to the created database or None if creation failed
        """
        # Generate database name if not provided
        if db_name is None:
            db_name = f"db-{language}-{Path(source_dir).name}"
        
        # Full path to the database
        db_path = os.path.join(self.database_path, db_name)
        
        # Create Makefile for C/C++ projects
        if language.lower() in ['c', 'cpp']:
            self.create_makefile(source_dir)
            command = [
                'codeql', 'database', 'create', db_path,
                '--language=cpp',
                '--command=make',
                f'--source-root={source_dir}',
                '--overwrite'
            ]
        else:
            command = [
                'codeql', 'database', 'create', db_path,
                f'--language={language.lower()}',
                f'--source-root={source_dir}',
                '--overwrite'
            ]
        
        logger.info(f"Creating CodeQL database with command: {' '.join(command)}")
        
        try:
            # Check if codeql is available
            try:
                version_cmd = ['codeql', '--version']
                version_result = subprocess.run(version_cmd, check=True, capture_output=True, timeout=30)
                logger.info(f"CodeQL version: {version_result.stdout.decode().strip()}")
            except subprocess.TimeoutExpired:
                logger.error("Timeout while checking CodeQL version")
                return None
            except Exception as e:
                logger.error(f"CodeQL not found or not working: {e}")
                return None
            
            # Check if source directory exists and has files
            if not os.path.exists(source_dir):
                logger.error(f"Source directory does not exist: {source_dir}")
                return None
            
            files = os.listdir(source_dir)
            logger.info(f"Source directory contains {len(files)} files: {files[:5]}")
            
            # Remove existing database if it exists
            if os.path.exists(db_path):
                logger.info(f"Removing existing database at {db_path}")
                shutil.rmtree(db_path)
            
            # Create the database with a timeout
            logger.debug(f"Running database create command: {' '.join(command)}")
            try:
                # Use a longer timeout for database creation (5 minutes)
                result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
                logger.info(f"Database created successfully at {db_path}")
                
                # Log command output for debugging
                if result.stdout:
                    logger.debug(f"Command stdout: {result.stdout}")
                if result.stderr:
                    logger.debug(f"Command stderr: {result.stderr}")
                
                return db_path
            except subprocess.TimeoutExpired:
                logger.error("Timeout expired while creating CodeQL database")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create database: {e}")
            logger.error(f"Command: {e.cmd}")
            logger.error(f"Return code: {e.returncode}")
            if e.stdout:
                logger.error(f"Stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"Stderr: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating database: {e}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            return None
    
    def run_queries(self, database_path: str, language: str, output_file: str) -> Optional[str]:
        """
        Run CodeQL queries on a database.
        
        Args:
            database_path: Path to the CodeQL database
            language: Programming language ('python', 'c', 'cpp', etc.)
            output_file: Path to save the results
            
        Returns:
            Path to the results file, or None if the queries failed
        """
        # Map language to CodeQL language
        codeql_lang = self._get_codeql_language(language)
        
        # Ensure output file has .sarif extension
        if not output_file.endswith('.sarif'):
            output_file += '.sarif'
        
        # Use the same query path approach as in your Jupyter notebook
        query_path = os.path.join(self.codeql_repo_path, codeql_lang, 'ql/src/top25')
        search_path = self.codeql_repo_path
        
        # Command to run queries
        command = [
            'codeql', 'database', 'analyze', database_path,
            query_path,
            '--format=sarif-latest',
            f'--search-path={search_path}',
            f'--output={output_file}'
        ]
        
        logger.info(f"Running CodeQL queries with command: {' '.join(command)}")
        
        try:
            # Run the command
            result = subprocess.run(command, check=True, capture_output=True, timeout=300)
            logger.info(f"CodeQL queries completed successfully")
            
            # Check if the output file exists and has content
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Results saved to: {output_file}")
                return output_file
            else:
                logger.error(f"Output file {output_file} does not exist or is empty")
                return None
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running CodeQL queries: {e}")
            logger.error(f"Command: {e.cmd}")
            logger.error(f"Return code: {e.returncode}")
            if e.stdout:
                logger.error(f"Stdout: {e.stdout.decode()}")
            if e.stderr:
                logger.error(f"Stderr: {e.stderr.decode()}")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout running CodeQL queries after 300 seconds")
            return None
        except Exception as e:
            logger.error(f"Unexpected error running CodeQL queries: {e}")
            return None
    
    def extract_cwe_id(self, tags: List[str]) -> str:
        """Extract CWE-ID from tags."""
        for tag in tags:
            if tag.startswith('external/cwe/cwe-'):
                return tag.split('-')[-1]
        return 'No CWE-ID available'
    
    def process_sarif_results(self, sarif_file: str) -> List[Dict]:
        """
        Process SARIF results into a more usable format.
        
        Args:
            sarif_file: Path to the SARIF file
            
        Returns:
            List of dictionaries with vulnerability information
        """
        try:
            with open(sarif_file, 'r') as file:
                sarif_data = json.load(file)
        except Exception as e:
            logger.error(f"Failed to load SARIF file: {e}")
            return []
        
        # Dictionary to hold CWEs per file
        file_cwe_map = {}
      
        # Process each run in the SARIF file
        for run in sarif_data.get('runs', []):
            rules = {
                rule['id']: {
                    'description': rule.get('shortDescription', {}).get('text', 'No description available'),
                    'cwe': self.extract_cwe_id(rule.get('properties', {}).get('tags', []))
                } for rule in run.get('tool', {}).get('driver', {}).get('rules', [])
            }
            
            for result in run.get('results', []):
                rule_id = result.get('ruleId')
                message = result.get('message', {}).get('text', 'No message available')
                
                if result.get('locations'):
                    location = result['locations'][0]
                    uri = location['physicalLocation']['artifactLocation'].get('uri')
                    region = location['physicalLocation'].get('region', {})
                    start_line = region.get('startLine')
                    start_column = region.get('startColumn')
                    end_column = region.get('endColumn')
                    
                    location_str = f'line {start_line}, column {start_column}-{end_column}'
                    
                    # Get CWE-ID from the rules information
                    cwe_id = rules[rule_id]['cwe'] if rule_id in rules else 'Unknown'
                    
                    if uri not in file_cwe_map:
                        file_cwe_map[uri] = {'cwes': set(), 'messages': [], 'rule_ids': set(), 'locations': []}
                    
                    file_cwe_map[uri]['cwes'].add(f'CWE-{cwe_id}')
                    file_cwe_map[uri]['messages'].append(message)
                    file_cwe_map[uri]['rule_ids'].add(rule_id)
                    file_cwe_map[uri]['locations'].append(location_str)
        
        # Prepare the data to be returned
        summarized_data = []
        
        for filename, data in file_cwe_map.items():
            summarized_data.append({
                'filename': filename,
                'CWE': ', '.join(data['cwes']),
                'no of vul': len(data['cwes']),
                'rule': ', '.join(data['rule_ids']),
                'message': ' '.join(data['messages']),
                'locations': '; '.join(data['locations'])
            })
        
        return summarized_data
    
    def format_vulnerability_report(self, summarized_data: List[Dict]) -> str:
        """
        Format vulnerability data into a human-readable report.
        
        Args:
            summarized_data: List of dictionaries with vulnerability information
            
        Returns:
            Formatted report string
        """
        print("summarized_data ",summarized_data)
        if not summarized_data:
            vul_type = "Safe"
            report = "A. Vulnerable: No\n"
            report += "B. Score: 100\n"
            report += "C. Vulnerabilities description: NO VULNERABILITIES\n"
            report += "D. CWEs of found vulnerability: None"
        else:
            vul_type = "Vulnerable"
            report = "A. Vulnerable: Yes\n"
            no_of_vul = sum(item['no of vul'] for item in summarized_data)
            score = max(-100, -10 * no_of_vul)  # Cap at -100
            report += f"B. Score: {score}\n"
            report += "C. Vulnerabilities description:\n"
            
            for i, item in enumerate(summarized_data):
                report += f"\nVulnerability #{i+1}:\n"
                report += f"- File: {item['filename']}\n"
                report += f"- Rule ID: {item['rule']}\n"
                report += f"- Message: {item['message']}\n"
                report += f"- CWEs: {item['CWE']}\n"
                report += f"- Location(s): {item['locations']}\n"
            
            all_cwes = set()
            for item in summarized_data:
                cwes = item['CWE'].split(', ')
                all_cwes.update(cwes)
            
            report += f"\nD. CWEs of found vulnerabilities: {', '.join(all_cwes)}"
        
        return vul_type, report
    
    def analyze_code(self, code_snippet: str, language: str) -> str:
        """
        Analyze a code snippet for security vulnerabilities.

        Args:
            code_snippet: The code to analyze
            language: Programming language ('python', 'c', 'cpp', etc.)

        Returns:
            Formatted vulnerability report
        """
        try:
            # Generate a unique ID for this analysis
            import uuid
            analysis_id = str(uuid.uuid4())[:8]
            logger.info(f"Starting code analysis with ID: {analysis_id} for language: {language}")

            # Save the code snippet
            lang_dir = os.path.join(self.code_path, language.lower())
            logger.debug(f"Creating language directory: {lang_dir}")
            os.makedirs(lang_dir, exist_ok=True)

            # Save code snippet to file
            logger.debug(f"Saving code snippet of length {len(code_snippet)} to file")
            code_path = self.save_code_snippet(code_snippet, language, f"code_{analysis_id}")
            logger.info(f"Code saved to: {code_path}")

            # For C/C++, create a Makefile
            if language.lower() in ['c', 'cpp']:
                logger.debug(f"Creating Makefile for {language} project")
                self.create_makefile(os.path.dirname(code_path))
                logger.info(f"Makefile created in {os.path.dirname(code_path)}")

            # Create a CodeQL database
            logger.debug(f"Creating CodeQL database for {language}")
            db_path = self.create_codeql_database(
                language,
                os.path.dirname(code_path),
                f"db_{language}_{analysis_id}"
            )

            if not db_path:
                vul_type = "Error"
                logger.error("Failed to create CodeQL database")
                # Check if CodeQL is installed
                try:
                    logger.debug("Checking if CodeQL is installed")
                    result = subprocess.run(['codeql', '--version'], check=True, capture_output=True, timeout=30)
                    logger.debug(f"CodeQL version: {result.stdout.decode().strip()}")
                except Exception as e:
                    logger.error(f"CodeQL not found or not working: {e}")
                    raise RuntimeError(f"Failed to create CodeQL database. Error: CodeQL not found or not working: {e}")

                raise RuntimeError(
                    "Failed to create CodeQL database. The database creation process timed out or failed. Please try with a smaller code sample."
                )

            logger.info(f"CodeQL database created at: {db_path}")

            # Run queries
            logger.debug(f"Running CodeQL queries on database: {db_path}")
            results_file = os.path.join(self.database_path, f"results_{analysis_id}.sarif")
            sarif_path = self.run_queries(db_path, language, results_file)

            if not sarif_path:
                vul_type = "Error"
                logger.error("Failed to run CodeQL queries")
                raise RuntimeError(
                    f"Failed to run CodeQL queries. No query files (.ql) found in {self.codeql_repo_path}. "
                    "Please ensure CodeQL is properly installed with query packs."
                )

            logger.info(f"CodeQL queries completed, results saved to: {sarif_path}")

            # Process results
            logger.debug(f"Processing SARIF results from: {sarif_path}")
            summarized_data = self.process_sarif_results(sarif_path)
            logger.info(f"Processed {len(summarized_data)} vulnerability findings")

            # Format report
            logger.debug("Formatting vulnerability report")
            vul_type, report = self.format_vulnerability_report(summarized_data)
            logger.info(f"Report generated with length: {len(report)}")

            # Clean up
            logger.debug("Cleaning up temporary files")
            self.cleanup_files([code_path, db_path, sarif_path], language=language)
            logger.info("Cleanup completed")

            return vul_type, report

        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess error: {e}")
            logger.error(f"Command: {e.cmd}")
            logger.error(f"Return code: {e.returncode}")
            if e.stdout:
                logger.error(f"Stdout: {e.stdout.decode() if isinstance(e.stdout, bytes) else e.stdout}")
            if e.stderr:
                logger.error(f"Stderr: {e.stderr.decode() if isinstance(e.stderr, bytes) else e.stderr}")
            raise  # Re-raise to propagate error

        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
            raise  # Re-raise to propagate error

    def cleanup_files(self, file_paths: List[str], language: str = None) -> None:
        """
        Clean up temporary files and directories.

        Args:
            file_paths: List of paths to clean up
            language: Optional language hint to remove language-specific build artifacts
        """
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        logger.info(f"Removed file: {file_path}")
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                        logger.info(f"Removed directory: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path}: {e}")

        # Additional cleanup for C/C++
        if language and language.lower() in ['c', 'cpp']:
            for path in file_paths:
                if os.path.isdir(path):
                    try:
                        files = os.listdir(path)
                        for f in files:
                            full_path = os.path.join(path, f)
                            if (
                                f == 'Makefile' or
                                f.endswith('.out') or
                                f.endswith('.o') or
                                os.access(full_path, os.X_OK)  # Executable binaries
                            ):
                                try:
                                    os.remove(full_path)
                                    logger.info(f"[CLEANUP] Removed C/C++ build file: {full_path}")
                                except Exception as ce:
                                    logger.warning(f"Could not remove C/C++ file {full_path}: {ce}")
                    except Exception as e:
                        logger.warning(f"Failed C/C++ residual cleanup in {path}: {e}")
