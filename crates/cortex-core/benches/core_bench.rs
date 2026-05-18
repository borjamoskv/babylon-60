use criterion::{black_box, criterion_group, criterion_main, Criterion};

pub fn dummy_benchmark(c: &mut Criterion) {
    c.bench_function("dummy", |b| b.iter(|| black_box(1)));
}

criterion_group!(benches, dummy_benchmark);
criterion_main!(benches);
