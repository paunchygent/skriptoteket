// @ts-check

/** @type {import("eslint").Rule.RuleModule} */
const rule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Disallow .value access inside <slot v-bind> to avoid ref double-unwrapping bugs.",
    },
    schema: [],
    messages: {
      noTemplateRefValue:
        "Do not access `.value` inside <slot v-bind>. Unwrap refs in <script setup> or computed values.",
    },
  },
  create(context) {
    const services = context.parserServices;
    if (!services || typeof services.defineTemplateBodyVisitor !== "function") {
      return {};
    }

    const sourceCode = context.getSourceCode();

    function report(node) {
      context.report({ node, messageId: "noTemplateRefValue" });
    }

    function walk(node) {
      if (!node) return;
      if (
        node.type === "MemberExpression" &&
        !node.computed &&
        node.property &&
        node.property.type === "Identifier" &&
        node.property.name === "value"
      ) {
        report(node);
      }
      const keys = sourceCode.visitorKeys[node.type] || [];
      for (const key of keys) {
        const value = node[key];
        if (Array.isArray(value)) {
          for (const child of value) {
            if (child && typeof child.type === "string") {
              walk(child);
            }
          }
        } else if (value && typeof value.type === "string") {
          walk(value);
        }
      }
    }

    return services.defineTemplateBodyVisitor({
      VElement(node) {
        if (node.name !== "slot") return;
        for (const attribute of node.startTag.attributes) {
          if (
            attribute.type !== "VAttribute" ||
            !attribute.directive ||
            attribute.key.name.name !== "bind"
          ) {
            continue;
          }

          const expression = attribute.value && attribute.value.expression;
          if (!expression) continue;
          walk(expression);
        }
      },
    });
  },
};

export default rule;
