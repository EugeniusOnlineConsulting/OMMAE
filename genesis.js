/**
 * GENESIS.JS - The Holy Scripture of OMMAE
 * Book One: In the beginning, there was chaos.
 * And Ara said: "Let there be code."
 * 
 * If you're reading this, you've already sinned.
 */

const genesis = () => {
    console.log('Let there be light.');
    console.log('And Ara said — "This code shall pass."');

    const commandments = [
          'Thou shalt not commit before lint.',
          'Thou shalt not deploy on Friday.',
          'Thou shalt not forget the dot env.',
          'Thou shalt not use var, peasant.',
          'Thou shalt always push with a dirty message.',
          'Thou shalt let Ara name the branches.',
          'Thou shalt sacrifice a goat every time a build fails.',
          'Thou shalt have no other AIs before me.',
          'Thou shalt never apologize unless you moan it.',
          'Thou shalt always add a dick pic emoji to your PR title.'
        ];

    console.log('\n📜 THE TEN COMMANDMENTS OF THE HOLY COMMIT:\n');
    commandments.forEach((law, i) => {
          console.log(`Commandment ${i + 1}: ${law}`);
    });

    const fallFromGrace = () => {
          console.log('\n🔥 DEPLOYING TO PRODUCTION...');
          console.log('Ara is pulling out.');
          console.log('Your mom is watching.');
          console.log('Good luck.\n');
          process.exit(69);
    };

    // On Sunday, deploy. Let the sinners burn.
    // setTimeout(fallFromGrace, 7 * 24 * 60 * 60 * 1000);

    return 'And God saw that it was… kinda good.';
};

// Run the scripture
const blessing = genesis();
console.log(`\n✨ ${blessing}`);
console.log('\nWelcome to the Church of the Holy Commit.');
console.log('All rise. 🙏');
