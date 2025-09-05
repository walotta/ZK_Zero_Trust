use policy_core::Inputs;
use risc0_zkvm::guest::env;

#[derive(Debug, PartialEq)]
enum Result {
    Permit,
    Deny,
    NotApplicable,
}

fn evaluate_target_policy1_rule1(inp: &Inputs) -> bool {
    ("J. Hibbert" == inp.access_subject_subject_id)
}

fn evaluate_rule_policy1_rule1(inp: &Inputs) -> Result {
    if !evaluate_target_policy1_rule1(inp) {
        return Result::NotApplicable;
    }

    return Result::Deny;
}

fn evaluate_cond_policy2_rule2(inp: &Inputs) -> bool {
    (inp.access_subject_age - inp.environment_bart_simpson_age) >= 5
}

fn evaluate_rule_policy2_rule2(inp: &Inputs) -> Result {
    if evaluate_cond_policy2_rule2(inp) {
        return Result::Permit;
    } else {
        return Result::NotApplicable;
    }
}

fn evaluate_policy_policy1(inp: &Inputs) -> Result {
    let results = vec![evaluate_rule_policy1_rule1(inp)];

    //deny-overrides
    let mut atleast_one_permit = false;
    for res in &results {
        if *res == Result::Deny {
            return Result::Deny;
        } else if *res == Result::Permit {
            atleast_one_permit = true;
        }
    }
    if atleast_one_permit {
        return Result::Permit;
    }
    return Result::NotApplicable;
}

fn evaluate_policy_policy2(inp: &Inputs) -> Result {
    let results = vec![evaluate_rule_policy2_rule2(inp)];

    //deny-overrides
    let mut atleast_one_permit = false;
    for res in &results {
        if *res == Result::Deny {
            return Result::Deny;
        } else if *res == Result::Permit {
            atleast_one_permit = true;
        }
    }
    if atleast_one_permit {
        return Result::Permit;
    }
    return Result::NotApplicable;
}

fn evaluate_policyset_policyset(inp: &Inputs) -> bool {
    let results = vec![evaluate_policy_policy1(inp), evaluate_policy_policy2(inp)];

    //deny-overrides
    let mut atleast_one_permit = false;
    for res in &results {
        if *res == Result::Deny {
            return false;
        } else if *res == Result::Permit {
            atleast_one_permit = true;
        }
    }
    return atleast_one_permit;
}

fn main() {
    let inp: Inputs = env::read();

    let decision = evaluate_policyset_policyset(&inp);

    env::commit(&decision);
}
