use crate::ast::AST;
use std::vec::Vec;

pub fn parse(_source: &str) -> AST {
    AST {
        instructions: Vec::new(),
    }
}
