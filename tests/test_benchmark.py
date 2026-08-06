from trading_system.data.benchmark import benchmark_intraday_ingestion


def test_chunked_ingestion_benchmark(tmp_path) -> None:
    output = tmp_path / "benchmark.json"
    result = benchmark_intraday_ingestion(
        rows=10_000,
        symbols=10,
        chunk_size=2_000,
        output_path=output,
    )
    assert result["rows_processed"] == 10_000
    assert result["aggregated_bars"] == 10
    assert output.exists()
