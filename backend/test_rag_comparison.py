"""Compare insights quality: WITHOUT RAG vs WITH RAG for customer_1 2024."""
import asyncio
import sys
import io
import os
from dotenv import load_dotenv

load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


async def main():
    from services.ocr_service import _parse_fields_spatial
    from services.tax_engine import estimated_liability, combined_marginal_rate
    from services.llm_service import analyze_financials
    from services.benefit_engine import generate_insights
    from services.lightrag_service import init_rag, query_tax_guidance

    # 1. Extract fields
    pdf_path = "../test_data/customer_1/T4_2024_Thompson.pdf"
    fields = _parse_fields_spatial(pdf_path)
    income = fields.get("14", 0)
    province = fields.get("province_code", "ON")
    tax_year = fields.get("tax_year", 2024)
    rrsp_room = 12000
    tfsa_room = 8500

    # 2. LLM analysis (shared)
    llm_result = analyze_financials(
        structured_fields=fields,
        rrsp_room=rrsp_room,
        tfsa_room=tfsa_room,
        province=province,
        tax_year=tax_year,
    )

    derived = {
        "estimated_tax_liability": estimated_liability(income, province, tax_year),
        "marginal_rate_combined": combined_marginal_rate(income, province, tax_year)[2],
    }

    print("=" * 70)
    print(f"  Sarah Thompson | ${income:,.0f} income | {province} | {tax_year}")
    print(f"  RRSP room: ${rrsp_room:,} | TFSA room: ${tfsa_room:,}")
    print(f"  Est. tax: ${derived['estimated_tax_liability']:,.2f} | Marginal: {derived['marginal_rate_combined']*100:.1f}%")
    print("=" * 70)

    # === WITHOUT RAG ===
    profile_no_rag = {
        "employment": {"total_employment_income": income},
        "registered_accounts": {"rrsp_room_remaining": rrsp_room, "tfsa_room_remaining": tfsa_room},
        "derived": derived,
    }
    result_no_rag = generate_insights(profile_no_rag, llm_result)

    print("\n>>> WITHOUT RAG <<<")
    print("-" * 50)
    for i, ins in enumerate(result_no_rag["insights"], 1):
        val = ins.get("estimated_value")
        val_str = f"${val:,.2f}" if val else "N/A"
        print(f"\n  [{i}] {ins['id']} | {ins['priority']} | {val_str}")
        print(f"      {ins['headline']}")
        print(f"      {ins['detail']}")
        if ins.get("calculation_shown"):
            print(f"      Calc: {ins['calculation_shown']}")
        if ins.get("action_required"):
            print(f"      Action: {ins['action_required']}")

    # === WITH RAG ===
    await init_rag()
    questions = [
        f"What are the RRSP contribution rules and tax benefits for {tax_year} with ${rrsp_room:.0f} contribution room?",
        f"What are the TFSA rules and contribution limits for {tax_year}?",
        f"What tax planning strategies apply for ${income:.0f} employment income in {province} for {tax_year}?",
    ]
    rag_context = []
    for q in questions:
        r = await query_tax_guidance(q, mode="hybrid")
        rag_context.append(r)

    profile_with_rag = {**profile_no_rag, "rag_context": rag_context}
    result_with_rag = generate_insights(profile_with_rag, llm_result)

    print("\n\n>>> WITH RAG <<<")
    print("-" * 50)
    for i, ins in enumerate(result_with_rag["insights"], 1):
        val = ins.get("estimated_value")
        val_str = f"${val:,.2f}" if val else "N/A"
        print(f"\n  [{i}] {ins['id']} | {ins['priority']} | {val_str}")
        print(f"      {ins['headline']}")
        detail = ins["detail"]
        if "\n\nCRA Guidance:" in detail:
            base, guidance = detail.split("\n\nCRA Guidance:", 1)
            print(f"      {base}")
            print(f"      --- CRA Knowledge Graph Context ---")
            print(f"      {guidance[:400].strip()}")
        else:
            print(f"      {detail}")
        if ins.get("calculation_shown"):
            print(f"      Calc: {ins['calculation_shown']}")
        if ins.get("action_required"):
            print(f"      Action: {ins['action_required']}")

    print("\n")
    print("=" * 70)
    print("  COMPARISON SUMMARY")
    print("=" * 70)
    print(f"  Without RAG: {len(result_no_rag['insights'])} insights, ${result_no_rag['summary']['total_identified_savings']:,.2f} total savings")
    print(f"  With RAG:    {len(result_with_rag['insights'])} insights, ${result_with_rag['summary']['total_identified_savings']:,.2f} total savings")
    print()
    print("  Quality difference:")
    print("    - Without RAG: Generic advice ('contributing can reduce taxable income')")
    print("    - With RAG:    Specific CRA rules, exact limits, deadlines, and strategies")
    print("                   backed by authoritative tax law knowledge graph")


asyncio.run(main())
