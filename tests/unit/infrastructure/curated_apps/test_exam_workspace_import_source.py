"""PDF bytes reach the PDF reader and Word bytes the Word reader at the import seams."""

from pathlib import Path

from dishka import make_container

from skriptoteket.di.exam_workspace import ExamWorkspaceProvider
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.import_file_format import is_pdf
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_import_source import (  # noqa: E501
    ImportLabelerSource,
    ImportSourceChunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
    PdfPlumberLabelerMarkdown,
)
from skriptoteket.protocols.exam_workspace import DocxExamChunkerProtocol, LabelerSource

FIXTURES = Path("tests/fixtures/exam_conversion")
PDF_CORPUS = FIXTURES / "pdf_corpus/bf26_english_1_unit_test_kap_1_2_med_facit.pdf"
DOCX_CORPUS = FIXTURES / "docx_corpus/bf26_english_1_unit_test_kap_1_2_med_facit.docx"


def test_is_pdf_reads_the_pdf_header_only():
    assert is_pdf(b"%PDF-1.7 fake")
    assert not is_pdf(b"PK\x03\x04 fake docx zip")
    assert not is_pdf(b"")
    assert not is_pdf(b" %PDF-")


class RecordingChunker:
    """A format reader fake that records its bytes and returns its fixed chunk."""

    def __init__(self, chunk: DocxChunk) -> None:
        self.received: list[bytes] = []
        self._chunk = chunk

    def chunk(self, *, content: bytes) -> tuple[DocxChunk, ...]:
        self.received.append(content)
        return (self._chunk,)


class RecordingLabelerSource:
    """A format projector fake that records its bytes and returns its fixed source."""

    def __init__(self, source: LabelerSource) -> None:
        self.received: list[bytes] = []
        self._source = source

    def source(self, *, content: bytes) -> LabelerSource:
        self.received.append(content)
        return self._source


def test_import_source_chunker_sends_each_format_to_its_reader():
    word_chunks = PythonDocxExamChunker().chunk(content=DOCX_CORPUS.read_bytes())
    assert len(word_chunks) >= 2
    docx_fake = RecordingChunker(word_chunks[0])
    pdf_fake = RecordingChunker(word_chunks[1])
    dispatcher = ImportSourceChunker(docx=docx_fake, pdf=pdf_fake)  # type: ignore[arg-type]

    pdf_bytes = b"%PDF-1.7 fake"
    docx_bytes = b"PK\x03\x04 fake docx zip"
    assert dispatcher.chunk(content=pdf_bytes) == (word_chunks[1],)
    assert dispatcher.chunk(content=docx_bytes) == (word_chunks[0],)
    assert pdf_fake.received == [pdf_bytes]
    assert docx_fake.received == [docx_bytes]


def test_import_labeler_source_sends_each_format_to_its_projector():
    docx_source = LabelerSource(chunks=(), images={}, unavailable={})
    pdf_source = PythonDocxLabelerMarkdown().source(content=DOCX_CORPUS.read_bytes())
    docx_fake = RecordingLabelerSource(docx_source)
    pdf_fake = RecordingLabelerSource(pdf_source)
    dispatcher = ImportLabelerSource(docx=docx_fake, pdf=pdf_fake)  # type: ignore[arg-type]

    pdf_bytes = b"%PDF-1.7 fake"
    docx_bytes = b"PK\x03\x04 fake docx zip"
    assert dispatcher.source(content=pdf_bytes) is pdf_source
    assert dispatcher.source(content=docx_bytes) is docx_source
    assert pdf_fake.received == [pdf_bytes]
    assert docx_fake.received == [docx_bytes]


def test_real_readers_chunk_the_word_exam_and_its_pdf():
    dispatcher = ImportSourceChunker(docx=PythonDocxExamChunker(), pdf=PdfPlumberExamChunker())
    assert len(dispatcher.chunk(content=DOCX_CORPUS.read_bytes())) > 0
    assert len(dispatcher.chunk(content=PDF_CORPUS.read_bytes())) > 0


def test_pdf_labeler_source_carries_the_chunker_anchors_in_order():
    content = PDF_CORPUS.read_bytes()
    chunks = PdfPlumberExamChunker().chunk(content=content)
    source = ImportLabelerSource(
        docx=PythonDocxLabelerMarkdown(), pdf=PdfPlumberLabelerMarkdown()
    ).source(content=content)
    assert [chunk.anchor for chunk in source.chunks] == [chunk.anchor for chunk in chunks]
    assert source.images == {}
    assert source.unavailable == {}


def test_the_job_chunker_the_container_provides_reads_a_pdf():
    container = make_container(ExamWorkspaceProvider(), skip_validation=True)

    chunker = container.get(DocxExamChunkerProtocol)

    assert chunker.chunk(content=PDF_CORPUS.read_bytes()) == PdfPlumberExamChunker().chunk(
        content=PDF_CORPUS.read_bytes()
    )
    assert chunker.chunk(content=DOCX_CORPUS.read_bytes()) == PythonDocxExamChunker().chunk(
        content=DOCX_CORPUS.read_bytes()
    )
