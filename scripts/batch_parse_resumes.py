"""CLI tool for batch parsing multiple resume files with fail-fast behavior."""

import sys
import json
import argparse
from pathlib import Path
import glob

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.input_builder import build_sample_input
from ops.parsing_errors import ResumeParsingError


def main():
    """Main CLI entry point for batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch parse multiple resume files (DOCX/PDF/TXT) into sample_input.json format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse all DOCX files in current directory
  python scripts/batch_parse_resumes.py --resumes *.docx --role "Senior Financial Analyst" --output-dir tests/fixtures/
  
  # Parse specific files
  python scripts/batch_parse_resumes.py --resumes resume1.pdf resume2.docx --role "Data Scientist" --output-dir out/parsed/
  
  # With job description file
  python scripts/batch_parse_resumes.py --resumes *.docx --role "Engineer" --jd-file jd.txt --output-dir out/
  
Note: Batch processing uses fail-fast behavior. If any resume fails to parse,
      the entire batch stops and exits with error code 1.
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--resumes',
        nargs='+',
        required=True,
        help='Resume files or glob pattern (e.g., *.docx)'
    )
    parser.add_argument(
        '--role',
        required=True,
        help='Target role/position for all resumes'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for JSON files'
    )
    
    # Optional arguments
    parser.add_argument(
        '--jd-text',
        help='Job description text (applied to all resumes)'
    )
    parser.add_argument(
        '--jd-file',
        help='Path to job description text file'
    )
    parser.add_argument(
        '--jd-url',
        help='URL to fetch job description from'
    )
    parser.add_argument(
        '--context',
        help='Additional context (applied to all resumes)'
    )
    parser.add_argument(
        '--no-metrics',
        action='store_true',
        help='Skip metrics extraction'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information'
    )
    
    args = parser.parse_args()
    
    # Expand glob patterns and find all resume files
    resume_files = []
    for pattern in args.resumes:
        if '*' in pattern or '?' in pattern:
            # Glob pattern
            matched = glob.glob(pattern)
            resume_files.extend(matched)
        else:
            # Direct file path
            resume_files.append(pattern)
    
    # Deduplicate and filter existing files
    resume_files = list(set(resume_files))
    existing_files = [f for f in resume_files if Path(f).exists()]
    
    if not existing_files:
        print("❌ Error: No resume files found", file=sys.stderr)
        sys.exit(1)
    
    # Validate and create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle JD input
    jd_text = None
    jd_url = None
    
    if args.jd_file:
        jd_file_path = Path(args.jd_file)
        if not jd_file_path.exists():
            print(f"❌ Error: JD file not found: {args.jd_file}", file=sys.stderr)
            sys.exit(1)
        with open(jd_file_path, 'r', encoding='utf-8') as f:
            jd_text = f.read()
    elif args.jd_text:
        jd_text = args.jd_text
    elif args.jd_url:
        jd_url = args.jd_url
    
    # Print batch summary
    print("\n" + "="*70)
    print("BATCH RESUME PARSING")
    print("="*70)
    print(f"Target role: {args.role}")
    print(f"Resume files: {len(existing_files)}")
    print(f"Output directory: {output_dir}")
    if jd_text or jd_url:
        print(f"Job description: {'Provided' if jd_text else 'URL: ' + jd_url}")
    else:
        print(f"Job description: Using placeholder (⚠️  must be replaced)")
    print("="*70)
    print()
    
    # Process each resume (fail-fast)
    successful = 0
    for i, resume_file in enumerate(existing_files, 1):
        resume_path = Path(resume_file)
        output_name = f"{resume_path.stem}_input.json"
        output_path = output_dir / output_name
        
        print(f"[{i}/{len(existing_files)}] Processing: {resume_path.name}")
        
        try:
            # Build input dict
            input_dict = build_sample_input(
                resume_path=str(resume_path),
                role=args.role,
                jd_text=jd_text,
                jd_url=jd_url,
                extra_context=args.context,
                extract_metrics_flag=not args.no_metrics
            )
            
            # Write to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(input_dict, f, indent=2)
            
            print(f"  ✅ Success: {output_path.name}")
            print(f"     Extracted {len(input_dict['bullets'])} bullets")
            successful += 1
            
        except ResumeParsingError as e:
            # Fail fast - stop entire batch
            print(f"  ❌ Error: {str(e)}", file=sys.stderr)
            print(f"\n⚠️  Batch stopped at file {i}/{len(existing_files)}", file=sys.stderr)
            print(f"Successfully processed: {successful} files", file=sys.stderr)
            print(f"Failed at: {resume_path.name}", file=sys.stderr)
            
            if args.debug:
                import traceback
                print("\n🐛 Debug traceback:", file=sys.stderr)
                traceback.print_exc()
            
            sys.exit(1)
        
        except Exception as e:
            # Unexpected error - also fail fast
            print(f"  ❌ Unexpected Error: {str(e)}", file=sys.stderr)
            print(f"\n⚠️  Batch stopped at file {i}/{len(existing_files)}", file=sys.stderr)
            
            if args.debug:
                import traceback
                print("\n🐛 Debug traceback:", file=sys.stderr)
                traceback.print_exc()
            
            sys.exit(2)
    
    # All successful
    print()
    print("="*70)
    print(f"✅ BATCH COMPLETE - All {successful} files processed successfully")
    print("="*70)
    
    if not jd_text and not jd_url:
        print("\n⚠️  REMINDER: Generated files use placeholder job description")
        print("   You must replace placeholders before running state machine")
    
    sys.exit(0)


if __name__ == "__main__":
    main()

