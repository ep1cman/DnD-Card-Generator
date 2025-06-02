import PyPDF2
from collections import defaultdict
import os
import argparse
import subprocess
import sys
import shutil

# Define size names
SIZE_NAMES = {
    "357x252": "Small",
    "714x252": "Large",      
    "714x357": "Epic",       
    "714x536": "Super_Epic"
}

def get_size_name(width, height):
    """Get friendly name for a given size"""
    size_key = f"{round(width)}x{round(height)}"
    return SIZE_NAMES.get(size_key, f"size_{size_key}")

def split_pdf_by_size(input_file):
    """Split a PDF into multiple files based on page dimensions"""

    # Open the PDF
    reader = PyPDF2.PdfReader(input_file)
    size_groups = defaultdict(list)

    # Group pages by size
    print(f"Analyzing {len(reader.pages)} pages...")
    for i, page in enumerate(reader.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        # Round to avoid floating point precision issues
        size_key = f"{round(width)}x{round(height)}"
        size_groups[size_key].append(i)

    # Create output files for each size group
    base_name = os.path.splitext(input_file)[0]
    output_files = []

    for size, page_indices in size_groups.items():
        # Get friendly name
        friendly_name = get_size_name(*map(int, size.split('x')))

        # Create a new PDF writer for this size group
        writer = PyPDF2.PdfWriter()

        # Add all pages of this size to the writer
        for idx in page_indices:
            writer.add_page(reader.pages[idx])

        # Generate output filename with friendly name
        output_filename = f"{base_name}_{friendly_name}.pdf"

        # Write the PDF
        with open(output_filename, 'wb') as output_file:
            writer.write(output_file)

        output_files.append(output_filename)

        # Print summary
        page_numbers = [str(i+1) for i in page_indices]  # Convert to 1-indexed
        print(f"\n{friendly_name} cards ({size}):")
        print(f"  - Pages: {', '.join(page_numbers[:10])}{'...' if len(page_numbers) > 10 else ''}")
        print(f"  - Total: {len(page_indices)} pages")
        print(f"  - Saved to: {output_filename}")

    return output_files, size_groups

def run_pdfjam_command(cmd):
    """Execute a pdfjam command"""
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Success")
        else:
            print(f"✗ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Failed to run command: {e}")
        return False
    return True

def process_nup(size_groups, base_name, do_merge=True, margin=None):
    """Generate and optionally run N-up commands"""
    print("\n" + "="*50)
    print("N-up Processing:")
    print("="*50)

    # Optimal layouts for each card type
    nup_settings = {
        "357x252": {"nup": "2x2", "landscape": True},   # Small: 4 per page, landscape
        "714x252": {"nup": "1x2", "landscape": True},   # Large: 2 per page, landscape
        "714x357": None,                                # Epic: Skip N-up
        "714x536": None                                 # Super Epic: Skip N-up
    }

    nup_files = []
    skipped = []

    for size, pages in size_groups.items():
        friendly_name = get_size_name(*map(int, size.split('x')))
        settings = nup_settings.get(size)

        # Skip N-up for Epic and Super Epic
        if settings is None:
            skipped.append(friendly_name)
            print(f"\n# {friendly_name} cards ({size}) - {len(pages)} pages:")
            print(f"# Skipping N-up processing (keeping as single pages)")
            continue

        nup = settings["nup"]
        use_landscape = settings["landscape"]

        filename = f"{base_name}_{friendly_name}.pdf"
        output = f"{base_name}_{friendly_name}_merged.pdf"
        nup_files.append(output)

        orientation = "landscape" if use_landscape else "portrait"
        print(f"\n# {friendly_name} cards ({size}) - {len(pages)} pages:")
        print(f"# Layout: {nup} = {eval(nup.replace('x', '*'))} cards per sheet ({orientation})")
        if margin:
            print(f"# Margin: {margin}")

        cmd = [
            "pdfjam",
            "--nup", nup,
            "--noautoscale", "true",  # Keep original size
            "--paper", "a4paper"
        ]

        # Add margin if specified
        if margin:
            cmd.extend(["--delta", margin])

        # Only add landscape flag when needed
        if use_landscape:
            cmd.append("--landscape")

        cmd.extend([
            "--outfile", output,
            filename
        ])

        if do_merge:
            if not run_pdfjam_command(cmd):
                print("Stopping due to error.")
                return None
        else:
            # Format command for display
            cmd_str = f"pdfjam --nup {nup} --noautoscale true \\\n"
            cmd_str += f"       --paper a4paper"
            if margin:
                cmd_str += f" --delta '{margin}'"
            if use_landscape:
                cmd_str += " --landscape"
            cmd_str += f" \\\n       --outfile {output} {filename}"
            print(cmd_str)

    if skipped:
        print(f"\nNote: {', '.join(skipped)} cards kept as single pages (no N-up processing)")

    return nup_files

def main():
    parser = argparse.ArgumentParser(
        description='Split PDF by page sizes and create N-up layouts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s cards.pdf                              # Split and merge (default)
  %(prog)s cards.pdf --margin "10mm 10mm"         # Add 10mm margins
  %(prog)s cards.pdf --margin "0.5in 0.25in"      # Different X/Y margins
  %(prog)s cards.pdf --no-merge                   # Just split, show commands

Margin format:
  "X Y" where X is horizontal spacing and Y is vertical spacing
  Units: mm, cm, in, pt (e.g., "10mm 10mm", "0.5in 0.5in")

Card types:
  Small (357x252): 2x2 layout in landscape (4 per page) -> *_Small_merged.pdf
  Large (714x252): 1x2 layout in landscape (2 per page) -> *_Large_merged.pdf
  Epic (714x357): No N-up (kept as single pages)
  Super Epic (714x536): No N-up (kept as single pages)
        """
    )

    parser.add_argument('input_pdf', help='Input PDF file path')
    parser.add_argument('--no-merge', action='store_true',
                        help='Only split and show commands without running N-up merge')
    parser.add_argument('-m', '--margin', type=str, default=None,
                        help='Margin/spacing between cards (e.g., "10mm 10mm")')

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: File '{args.input_pdf}' not found!")
        sys.exit(1)

    # Validate margin format if provided
    if args.margin:
        margin_parts = args.margin.strip().split()
        if len(margin_parts) != 2:
            print("Error: Margin must be in format 'X Y' (e.g., '10mm 10mm')")
            sys.exit(1)

    # Determine if we should do merge (default is True)
    do_merge = not args.no_merge

    # Check for required tools if merging
    if do_merge:
        if shutil.which('pdfjam') is None:
            print("Error: 'pdfjam' is not installed or not in PATH!")
            print("Please install pdfjam first.")
            print("Alternatively, use --no-merge to just split the PDF.")
            sys.exit(1)

    try:
        # Split the PDF
        base_name = os.path.splitext(args.input_pdf)[0]
        output_files, size_groups = split_pdf_by_size(args.input_pdf)

        # Process N-up
        nup_files = process_nup(size_groups, base_name, do_merge=do_merge, margin=args.margin)

        # Summary
        print("\n" + "="*50)
        print("Card type summary:")
        print("="*50)
        for size, pages in size_groups.items():
            friendly_name = get_size_name(*map(int, size.split('x')))
            print(f"{friendly_name}: {len(pages)} cards")

        if do_merge and nup_files:
            print(f"\n✓ Complete! Created {len(nup_files)} merged PDF files")
            if args.margin:
                print(f"   Applied margin: {args.margin}")
            print("\nOutput files:")
            for nup_file in nup_files:
                print(f"  - {nup_file}")
        elif not do_merge:
            print("\n✓ Split complete! Use without --no-merge to create merged PDFs")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
