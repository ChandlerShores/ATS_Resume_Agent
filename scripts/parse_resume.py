"""CLI tool for parsing a single resume file into sample_input.json format."""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ops.input_builder import build_sample_input, preview_extraction
from ops.parsing_errors import ResumeParsingError


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Parse resume file (DOCX/PDF/TXT) into sample_input.json format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with placeholder JD
  python scripts/parse_resume.py --resume john_walker_test.docx --role "Senior Financial Analyst" --output tests/john_input.json
  
  # With job description text
  python scripts/parse_resume.py --resume resume.pdf --role "Data Scientist" --jd-text "We are seeking..." --output input.json
  
  # With job description file
  python scripts/parse_resume.py --resume resume.docx --role "Engineer" --jd-file jd.txt --output input.json
  
  # Preview mode (no output file)
  python scripts/parse_resume.py --resume resume.docx --role "Analyst" --preview
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--resume',
        required=True,
        help='Path to resume file (DOCX, PDF, or TXT)'
    )
    parser.add_argument(
        '--role',
        required=True,
        help='Target role/position (e.g., "Senior Financial Analyst")'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output',
        help='Output path for JSON file (e.g., tests/input.json)'
    )
    parser.add_argument(
        '--jd-text',
        help='Job description text (inline)'
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
        help='Additional context about role/candidate'
    )
    parser.add_argument(
        '--no-metrics',
        action='store_true',
        help='Skip metrics extraction'
    )
    parser.add_argument(
        '--preview',
        action='store_true',
        help='Preview extraction without saving (useful for testing)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information'
    )
    
    args = parser.parse_args()
    
    # Validate resume file exists
    resume_path = Path(args.resume)
    if not resume_path.exists():
        print(f"❌ Error: Resume file not found: {args.resume}", file=sys.stderr)
        sys.exit(1)
    
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
    
    # Preview mode
    if args.preview:
        print("\n" + "="*70)
        print("PREVIEW MODE - Extraction Summary")
        print("="*70)
        print(preview_extraction(str(resume_path), args.role))
        print("="*70)
        print("\n✅ Preview complete. Use --output to save to JSON file.")
        sys.exit(0)
    
    # Validate output path provided
    if not args.output:
        print("❌ Error: --output is required (or use --preview)", file=sys.stderr)
        sys.exit(1)
    
    # Parse and build input
    try:
        print(f"\n📄 Parsing resume: {resume_path.name}")
        print(f"🎯 Target role: {args.role}")
        
        input_dict = build_sample_input(
            resume_path=str(resume_path),
            role=args.role,
            jd_text=jd_text,
            jd_url=jd_url,
            extra_context=args.context,
            extract_metrics_flag=not args.no_metrics
        )
        
        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(input_dict, f, indent=2)
        
        # Success message
        print(f"\n✅ Successfully created: {output_path}")
        print(f"   Extracted {len(input_dict['bullets'])} bullets")
        
        # Show metrics summary if extracted
        if input_dict.get('metrics'):
            metrics = input_dict['metrics']
            metric_count = (
                len(metrics.get('percentages', [])) +
                len(metrics.get('dollar_amounts', [])) +
                len(metrics.get('counts', {})) +
                len(metrics.get('time_periods', []))
            )
            if metric_count > 0:
                print(f"   Extracted {metric_count} metrics")
        
        # Warn if using placeholder JD
        if not jd_text and not jd_url:
            print("\n⚠️  WARNING: Using placeholder job description")
            print("   You must replace this with actual JD before running state machine")
        
        if args.debug:
            print("\n📊 Debug info:")
            print(f"   Output file size: {output_path.stat().st_size} bytes")
            print(f"   Bullets extracted: {len(input_dict['bullets'])}")
        
        sys.exit(0)
    
    except ResumeParsingError as e:
        print(f"\n❌ Parsing Error: {str(e)}", file=sys.stderr)
        
        if args.debug:
            import traceback
            print("\n🐛 Debug traceback:", file=sys.stderr)
            traceback.print_exc()
        
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}", file=sys.stderr)
        
        if args.debug:
            import traceback
            print("\n🐛 Debug traceback:", file=sys.stderr)
            traceback.print_exc()
        
        sys.exit(2)


if __name__ == "__main__":
    main()

