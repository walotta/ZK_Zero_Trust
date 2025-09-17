

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
#[serde(default)]
pub struct Inputs {
    pub access_subject_subject_id: String,
    pub access_subject_age: i32,
    pub environment_bart_simpson_age: i32,
}

impl Inputs {
    pub fn new(access_subject_subject_id: String, access_subject_age: i32, environment_bart_simpson_age: i32) -> Self {
        Self {
            access_subject_subject_id,
            access_subject_age,
            environment_bart_simpson_age,
        }
    }
}