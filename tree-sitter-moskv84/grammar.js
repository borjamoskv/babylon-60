module.exports = grammar({
  name: 'moskv84',

  extras: $ => [
    /\s/,
    $.comment
  ],

  rules: {
    source_file: $ => repeat($._statement),

    _statement: $ => choice(
      $.axiom_declaration,
      $.mutation_declaration,
      $.swarm_function,
      $.expression_statement
    ),

    axiom_declaration: $ => seq(
      'axiom',
      field('name', $.identifier),
      ':',
      field('type', $.type_identifier),
      '=',
      field('value', $.expression),
      ';'
    ),

    mutation_declaration: $ => seq(
      'mutation',
      field('name', $.identifier),
      '(',
      optional($.parameter_list),
      ')',
      optional(seq('->', field('return_type', $.type_identifier))),
      $.block
    ),

    swarm_function: $ => seq(
      'swarm',
      'fn',
      field('name', $.identifier),
      '(',
      optional($.parameter_list),
      ')',
      optional(seq('->', field('return_type', $.type_identifier))),
      $.block
    ),

    parameter_list: $ => commaSep1($.parameter),
    
    parameter: $ => seq(
      field('name', $.identifier),
      ':',
      field('type', $.type_identifier)
    ),

    block: $ => seq(
      '{',
      repeat($._statement),
      '}'
    ),

    expression_statement: $ => seq(
      $.expression,
      ';'
    ),

    expression: $ => choice(
      $.identifier,
      $.number,
      $.string,
      $.call_expression
    ),

    call_expression: $ => seq(
      field('function', $.identifier),
      '(',
      optional(commaSep1($.expression)),
      ')'
    ),

    identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,
    type_identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,
    number: $ => /\d+(_\d+)*/,
    string: $ => /"[^"]*"/,

    comment: $ => token(seq('//', /.*/))
  }
});

function commaSep1(rule) {
  return seq(rule, repeat(seq(',', rule)));
}
