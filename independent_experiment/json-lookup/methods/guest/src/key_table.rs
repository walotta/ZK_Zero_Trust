use serde::Deserialize;

macro_rules! define_schema {
    ($($field:ident),* $(,)?) => {
        pub const KEY_TABLE: &[&str] = &[
            $(stringify!($field)),*
        ];

        #[derive(Deserialize)]
        pub struct Outputs {
            $(pub $field: String,)*
        }

        impl Outputs {
            pub fn into_vec(self) -> Vec<String> {
                vec![
                    $(self.$field),*
                ]
            }
        }
    };
}

define_schema!(
    iss,
    subject_id,
    aud,
    exp,
    iat,
    auth_time,
    email,
    email_verified,
    nonce,
    scope,
    roles,
);
