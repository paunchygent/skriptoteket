<script lang="ts">
/**
 * Read-only rich text.
 *
 * Domain purpose:
 *   Render one text run with the marks the native document stores, as the
 *   same strong/em/u/sup/sub elements the editor and the QTI export use.
 *   Nothing here interprets markup or accepts HTML, so a shared instruction
 *   and a row preview show exactly the stored text and marks.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceSharedInstruction`.
 *   - Reads marks from `examWorkspaceBodyMarks`.
 */

import { h, type PropType, type VNodeChild } from "vue";

import { canonicalMarks, MARK_TAGS } from "./examWorkspaceBodyMarks";
import type { BodyMark } from "./examWorkspaceBodyMarks";

export default {
  name: "ExamWorkspaceRichText",
  props: {
    text: { type: String, required: true },
    marks: { type: Array as PropType<BodyMark[]>, default: () => [] },
  },
  setup(props) {
    return (): VNodeChild =>
      canonicalMarks(props.marks).reduceRight<VNodeChild>(
        (child, mark) => h(MARK_TAGS[mark], [child]),
        props.text,
      );
  },
};
</script>
