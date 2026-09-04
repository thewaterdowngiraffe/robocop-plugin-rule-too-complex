import re
from robocop.linter.rules import FixableRule, RuleSeverity, VisitorChecker
from robocop.linter.fix import Fix, FixAvailability, FixApplicability, TextEdit
# https://robocop.dev/stable/linter/custom_rules


class LogicCanBeSimplifiedRule(FixableRule):
    name = "logic-can-be-simplified"
    rule_id = "9901"
    message = "Inline evaluation is too complex.\n" \
        "Found: '{issue_detail}'.\n" \
        "Suggested fix: '{suggested_fix}'"
    severity = RuleSeverity.INFO
    # Tell Robocop this rule supports auto-fixing
    fix_availability = FixAvailability.ALWAYS


class SimplifyLogicChecker(VisitorChecker):
    simplify_rule: LogicCanBeSimplifiedRule

    def __init__(self):
        super().__init__()

        self.block_regex = re.compile(r"(?<=\$[\{]{2}).*(?=[\}]{2})")
        self.complexity_regex = re.compile(
            r"(['\"]{1,3})?\$\{{1,2}[^\}\{]*\}{1,2}(['\"]{1,3})?")
        self.fix_extraction_regex = re.compile(
            r"""(?:['"]{1,3})?\$\{{1,2}(?:\$(?=\b))?([^\}\{]*)(?=\}{1,2}(?:['"]{1,3})?)""")

    def visit(self, node):
        if hasattr(node, 'data_tokens'):
            for token in node.data_tokens:
                if token.value and isinstance(token.value, str):

                    for match in self.block_regex.finditer(token.value):
                        inline_logic = match.group(0)
                        rlist = re.findall(
                            r'(?=[\}]{2}).*(?<=\$[\{]{2})', inline_logic)

                        for o in range(len(rlist)):
                            inline_logic = re.sub(
                                r'(?=[\}]{2}).*(?<=\$[\{]{2})', f"~"*len(rlist[o]), inline_logic, count=1)
                            # inline_logic = tmp.replace(rlist[o], f"~"*len(rlist[o]))
                        # inline_logic = tmp  # match.group(0)
                        complex_match = self.complexity_regex.search(
                            inline_logic)

                        if complex_match:
                            issue_text = complex_match.group(0)
                            fix_match = self.fix_extraction_regex.search(
                                issue_text)

                            if fix_match:
                                raw_inner = fix_match.group(1)
                                suggested_fix = f"${raw_inner}"
                            else:
                                suggested_fix = issue_text  # Fallback

                            # Calculate precise coordinates for the TextEdit
                            start_col = token.col_offset + match.start() + complex_match.start() + 1
                            end_col = token.col_offset + match.start() + complex_match.end() + 1

                            # 1. Define exactly what text to replace and where
                            edit = TextEdit(
                                rule_id=self.simplify_rule.rule_id,
                                rule_name=self.simplify_rule.name,
                                start_line=token.lineno,
                                end_line=token.lineno,
                                start_col=start_col,
                                end_col=end_col,
                                replacement=suggested_fix
                            )

                            # 2. Wrap the edit in a Fix object
                            fix = Fix(
                                edits=[edit],
                                message=f"Simplify inline logic to {suggested_fix}",
                                applicability=FixApplicability.SAFE
                            )

                            # 3. Report the issue and pass the fix object
                            self.report(
                                self.simplify_rule,
                                issue_detail=issue_text,
                                suggested_fix=suggested_fix,
                                node=node,
                                lineno=token.lineno,
                                col=start_col,
                                end_col=end_col,
                                fix=fix  # Pass the fix directly to the reporter
                            )

        super().visit(node)
