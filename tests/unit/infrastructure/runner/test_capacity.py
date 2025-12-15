import pytest

from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter


@pytest.mark.asyncio
async def test_try_acquire_when_available_returns_true() -> None:
    limiter = RunnerCapacityLimiter(max_concurrency=2)

    result = await limiter.try_acquire()

    assert result is True


@pytest.mark.asyncio
async def test_try_acquire_when_at_capacity_returns_false() -> None:
    limiter = RunnerCapacityLimiter(max_concurrency=1)
    await limiter.try_acquire()

    result = await limiter.try_acquire()

    assert result is False


@pytest.mark.asyncio
async def test_release_after_acquire_restores_availability() -> None:
    limiter = RunnerCapacityLimiter(max_concurrency=1)
    await limiter.try_acquire()
    await limiter.release()

    result = await limiter.try_acquire()

    assert result is True


@pytest.mark.asyncio
async def test_release_without_acquire_raises_runtime_error() -> None:
    limiter = RunnerCapacityLimiter(max_concurrency=1)

    with pytest.raises(RuntimeError, match="released too many times"):
        await limiter.release()


def test_init_with_zero_concurrency_raises_value_error() -> None:
    with pytest.raises(ValueError, match="max_concurrency must be >= 1"):
        RunnerCapacityLimiter(max_concurrency=0)


def test_init_with_negative_concurrency_raises_value_error() -> None:
    with pytest.raises(ValueError, match="max_concurrency must be >= 1"):
        RunnerCapacityLimiter(max_concurrency=-1)


def test_max_concurrency_property_returns_configured_value() -> None:
    limiter = RunnerCapacityLimiter(max_concurrency=5)

    assert limiter.max_concurrency == 5
