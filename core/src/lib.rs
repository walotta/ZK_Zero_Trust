

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
#[serde(default)]
pub struct Inputs {
    // pub access_subject_subject_id: String,
    pub jwt: String,
}

impl Inputs {
    pub fn new(jwt: String) -> Self {
        Self {
            jwt
        }
    }
}
